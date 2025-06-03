"""
Streamlit GUI for GitHub PR Analysis Dashboard
"""
import streamlit as st
from src.config.settings import Settings
from src.db.database import Database
import logging
from datetime import datetime

# ロギングの設定
logger = logging.getLogger(__name__)

def main():
    """
    Streamlitアプリケーションのメイン関数
    """
    st.set_page_config(layout="wide", page_title="GitHub PR Analysis Dashboard")
    st.title("GitHub PR Analysis Dashboard")

    try:
        # 設定の読み込み
        settings = Settings()
        logger.info("設定を読み込みました")

        # データベース接続の初期化
        # settings.sqlite_db_path を使用して Database を初期化
        db_config = {'db_path': settings.sqlite_db_path}
        db = Database(db_config)
        logger.info(f"データベースオブジェクトを初期化しました (Path: {settings.sqlite_db_path})")

        # テーブル作成（存在しない場合のみ）
        # create_tables は冪等であるべき
        db.create_tables()
        logger.info("データベーステーブルの確認/作成が完了しました")

        # リポジトリリストの取得
        st.sidebar.header("Repositories")
        repositories = db.get_repository_list()

        if repositories:
            st.sidebar.subheader("Available Repositories")
            repo_names = [f"{repo['owner_login']}/{repo['name']}" for repo in repositories]
            selected_repo_name = st.sidebar.selectbox("Select a repository", repo_names)

            if selected_repo_name:
                st.header(f"Details for {selected_repo_name}")
                selected_repo_data = next(item for item in repositories if f"{item['owner_login']}/{item['name']}" == selected_repo_name)
                repo_id = selected_repo_data['id']

                # プルリクエストの取得と表示
                st.subheader("Pull Requests")
                all_pull_requests = db.get_pull_requests_for_repository(repo_id)

                filtered_prs = all_pull_requests

                # フィルタリングセクション
                with st.expander("Filter Pull Requests", expanded=True):
                    # 状態フィルタ
                    # PRの実際の状態値を取得 (例: 'open', 'closed')
                    available_states = sorted(list(set(pr['state'] for pr in all_pull_requests)))
                    selected_states = st.multiselect(
                        "Filter by State:",
                        options=available_states,
                        default=[] # 最初は何も選択しない
                    )

                    # 日付フィルタ
                    # created_at は文字列なので、datetime.dateオブジェクトに変換する必要がある
                    # None チェックも重要
                    pr_dates = [datetime.strptime(pr['created_at'].split(" ")[0], "%Y-%m-%d").date() for pr in all_pull_requests if pr.get('created_at')]

                    min_date = min(pr_dates) if pr_dates else datetime.today().date()
                    max_date = max(pr_dates) if pr_dates else datetime.today().date()

                    start_date = st.date_input("Start Date:", value=min_date, min_value=min_date, max_value=max_date)
                    end_date = st.date_input("End Date:", value=max_date, min_value=min_date, max_value=max_date)

                # フィルタ適用
                if selected_states:
                    filtered_prs = [pr for pr in filtered_prs if pr['state'] in selected_states]

                if start_date:
                    filtered_prs = [
                        pr for pr in filtered_prs if pr.get('created_at') and
                        datetime.strptime(pr['created_at'].split(" ")[0], "%Y-%m-%d").date() >= start_date
                    ]

                if end_date:
                    filtered_prs = [
                        pr for pr in filtered_prs if pr.get('created_at') and
                        datetime.strptime(pr['created_at'].split(" ")[0], "%Y-%m-%d").date() <= end_date
                    ]

                if filtered_prs:
                    df_display_pr = [
                        {
                            "Number": pr["number"],
                            "Title": pr["title"],
                            "Author": pr["user_login"],
                            "State": pr["state"],
                            "Created At": pr["created_at"], # 元の文字列形式で表示
                            "Updated At": pr["updated_at"],
                            "URL": pr["url"]
                        } for pr in filtered_prs
                    ]
                    st.dataframe(df_display_pr)

                    # --- PR Selection and Details ---
                    st.markdown("---") # Visual separator
                    pr_options = {f"#{pr['number']} - {pr['title']}": pr for pr in filtered_prs}
                    select_box_options = ["Select a PR to view details..."] + list(pr_options.keys())

                    selected_pr_title_option = st.selectbox(
                        "Select PR for Details:",
                        options=select_box_options,
                        index=0 # Default to "Select a PR..."
                    )

                    if selected_pr_title_option != "Select a PR to view details...":
                        selected_pr_data = pr_options[selected_pr_title_option]

                        st.subheader("PR Details")
                        st.markdown(f"### {selected_pr_data['title']} (#{selected_pr_data['number']})")
                        st.caption(f"Author: {selected_pr_data['user_login']} | State: {selected_pr_data['state']}")

                        st.markdown(f"[View PR on GitHub]({selected_pr_data['url']})")

                        st.markdown("---")
                        st.subheader("Description")
                        if selected_pr_data['body'] and selected_pr_data['body'].strip():
                            st.markdown(selected_pr_data['body'])
                        else:
                            st.info("No description provided for this PR.")

                        # --- Review Comments ---
                        st.markdown("---")
                        st.subheader("Review Comments")
                        # The 'id' key was added to pull_requests in the previous subtask for this purpose
                        comments = db.get_review_comments_for_pr(selected_pr_data['id'])

                        if comments:
                            for comment in comments:
                                st.markdown(f"**{comment['user_login']}** commented on {comment['created_at']}:")
                                st.markdown(comment['body'])
                                st.markdown(f"[View Comment on GitHub]({comment['html_url']})")
                                st.divider()
                        else:
                            st.info("No review comments found for this PR.")

                elif not all_pull_requests: # 元々PRがなかった場合
                    st.info(f"No pull requests found for {selected_repo_name}.")
                else: # フィルタによって結果が0件になった場合
                    st.info("No pull requests match the current filter criteria.")
        else:
            st.sidebar.info("No repositories found in the database. Please add repositories first via CLI or configuration.")
            st.info("No repositories loaded. Please ensure repositories are configured and data is fetched.")

    except ValueError as ve:
        logger.error(f"設定エラー: {ve}")
        st.error(f"Configuration Error: {ve}. Please check your environment variables or config.yaml.")
    except Exception as e:
        logger.error(f"アプリケーションの実行中に予期せぬエラーが発生しました: {e}", exc_info=True)
        st.error(f"An unexpected error occurred: {e}")
        st.error("Please check the logs for more details. Ensure the database is accessible and configured correctly.")


if __name__ == '__main__':
    main()
