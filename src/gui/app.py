"""
Streamlit GUI for GitHub PR Analysis Dashboard
"""
try:
    import streamlit as st
except ImportError:
    st = None  # Handle missing streamlit gracefully
from src.gui.data_manager import DataManager
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple

# ロギングの設定
logger = logging.getLogger(__name__)

# Helper functions for Streamlit UI elements
def display_sidebar(data_manager: DataManager) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str], Optional[Dict[str, Any]]]:
    """Displays the sidebar for repository selection and returns selected repo info."""
    st.sidebar.header("Repositories")

    # DBにデータ投入ボタン
    st.sidebar.subheader("データ管理")
    if st.sidebar.button("🔄 DBにデータ投入", help="GitHub APIからデータを取得してDBに保存します"):
        # メインエリアでプログレスバーのみ表示
        with st.container():
            st.subheader("📊 データ取得・保存処理")
            
            # プログレスバーと現在の処理状況表示
            progress_bar = st.progress(0)
            current_status = st.empty()
            
            def progress_callback(message: str, level: str, progress: float):
                """進行状況を受け取るコールバック関数（画面には簡潔な情報のみ表示）"""
                # プログレスバーを更新
                if progress is not None:
                    progress_bar.progress(progress)
                
                # 現在の処理状況を表示（簡潔に）
                if level == 'error':
                    current_status.error(f"❌ {message}")
                elif level == 'warning':
                    current_status.warning(f"⚠️ {message}")
                else:
                    current_status.info(f"🔄 {message}")
            
            try:
                # コールバック付きでデータ取得を実行（詳細ログはコンソールに出力）
                success, message = data_manager.fetch_and_store_all_data(progress_callback)
                
                # 最終結果を表示
                if success:
                    current_status.success(f"✅ {message}")
                    st.info("💡 データが更新されました。リポジトリリストが更新されるまで少しお待ちください。")
                else:
                    current_status.error(f"❌ {message}")
                    
            except Exception as e:
                current_status.error(f"❌ 処理中にエラーが発生しました: {e}")
                logger.error(f"データ取得処理中のエラー: {e}", exc_info=True)
            finally:
                progress_bar.empty()

    st.sidebar.markdown("---")

    repositories, error_msg = data_manager.get_repositories()

    if error_msg:
        st.sidebar.error(f"Error loading repositories: {error_msg}")
        return None, None, None # Return tuple of Nones

    if not repositories:
        st.sidebar.info("No repositories found. Configure and fetch data first.")
        return None, None, None # Return tuple of Nones

    st.sidebar.subheader("Available Repositories")
    repo_names = [f"{repo['owner_login']}/{repo['name']}" for repo in repositories]
    selected_repo_name = st.sidebar.selectbox("Select a repository", repo_names)

    if selected_repo_name:
        selected_repo_data = next(item for item in repositories if f"{item['owner_login']}/{item['name']}" == selected_repo_name)
        return repositories, selected_repo_name, selected_repo_data
    return repositories, None, None # Return selected_repo_name and data as None if not selected


def display_pr_filters(all_pull_requests: List[Dict[str, Any]]) -> Tuple[List[str], Optional[datetime.date], Optional[datetime.date]]:
    """Displays PR filters and returns selected filter values."""
    with st.expander("Filter Pull Requests", expanded=True):
        available_states = sorted(list(set(pr['state'] for pr in all_pull_requests if pr.get('state'))))
        selected_states = st.multiselect("Filter by State:", options=available_states, default=[])

        pr_datetimes = [pr['created_at_dt'] for pr in all_pull_requests if pr.get('created_at_dt')]
        pr_dates = [dt.date() for dt in pr_datetimes if dt]

        min_date = min(pr_dates) if pr_dates else datetime.today().date()
        max_date = max(pr_dates) if pr_dates else datetime.today().date()

        start_date = st.date_input("Start Date:", value=min_date, min_value=min_date, max_value=max_date)
        end_date = st.date_input("End Date:", value=max_date, min_value=min_date, max_value=max_date)
        return selected_states, start_date, end_date


def apply_filters(
    all_pull_requests: List[Dict[str, Any]],
    selected_states: List[str],
    start_date: Optional[datetime.date],
    end_date: Optional[datetime.date]
) -> List[Dict[str, Any]]:
    """Applies filters to the list of pull requests."""
    filtered_prs = all_pull_requests
    if selected_states:
        filtered_prs = [pr for pr in filtered_prs if pr.get('state') in selected_states]
    if start_date:
        filtered_prs = [pr for pr in filtered_prs if pr.get('created_at_dt') and pr['created_at_dt'].date() >= start_date]
    if end_date:
        filtered_prs = [pr for pr in filtered_prs if pr.get('created_at_dt') and pr['created_at_dt'].date() <= end_date]
    return filtered_prs


def display_pr_list_and_get_selection(filtered_prs: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Displays the list of PRs and returns the selected PR for detail view."""
    df_display_pr = [{
        "Number": pr["number"], "Title": pr["title"], "Author": pr["user_login"],
        "State": pr["state"], "Created At": pr["created_at"],
        "Updated At": pr["updated_at"], "URL": pr["url"]
    } for pr in filtered_prs]
    st.dataframe(df_display_pr)

    st.markdown("---")
    pr_options = {f"#{pr['number']} - {pr['title']}": pr for pr in filtered_prs}
    select_box_options = ["Select a PR to view details..."] + list(pr_options.keys())
    selected_pr_title_option = st.selectbox("Select PR for Details:", options=select_box_options, index=0)

    if selected_pr_title_option != "Select a PR to view details...":
        return pr_options[selected_pr_title_option]
    return None


def display_pr_details(selected_pr_data: Dict[str, Any], data_manager: DataManager):
    """Displays the details of a selected pull request."""
    st.subheader("PR Details")
    st.markdown(f"### {selected_pr_data['title']} (#{selected_pr_data['number']})")
    st.caption(f"Author: {selected_pr_data['user_login']} | State: {selected_pr_data['state']}")
    st.markdown(f"[View PR on GitHub]({selected_pr_data['url']})")

    st.markdown("---")
    st.subheader("Description")
    if selected_pr_data.get('body') and selected_pr_data['body'].strip():
        st.markdown(selected_pr_data['body'])
    else:
        st.info("No description provided for this PR.")

    st.markdown("---")
    st.subheader("Review Comments")
    comments, comment_error_msg = data_manager.get_review_comments(selected_pr_data['id'])
    if comment_error_msg:
        st.error(f"Error loading review comments: {comment_error_msg}")
    elif comments:
        for comment in comments:
            # Display original created_at string for comments
            created_at_display = comment.get('created_at', 'N/A')
            st.markdown(f"**{comment['user_login']}** commented on {created_at_display}:")
            st.markdown(comment['body'])
            st.markdown(f"[View Comment on GitHub]({comment['html_url']})")
            st.divider()
    else:
        st.info("No review comments found for this PR.")


def display_lead_time_filters(data_manager: DataManager, repo_id: int) -> Tuple[Optional[datetime], Optional[datetime], Optional[str], bool]:
    """
    Display filter UI components for lead time analysis.
    
    Args:
        data_manager: DataManager instance for database access
        repo_id: Repository ID
        
    Returns:
        Tuple of (start_date, end_date, author, filters_applied)
        
    Requirements addressed: 3.1, 3.2, 3.3
    """
    with st.expander("🔍 Filter Settings", expanded=True):
        col1, col2, col3 = st.columns(3)
        
        # Date range filters
        with col1:
            st.markdown("**Date Range**")
            start_date = st.date_input(
                "Start Date",
                value=None,
                help="Filter PRs created on or after this date",
                key="lead_time_start_date"
            )
            
        with col2:
            st.markdown("**&nbsp;**")  # Spacing
            end_date = st.date_input(
                "End Date", 
                value=None,
                help="Filter PRs created on or before this date",
                key="lead_time_end_date"
            )
            
        with col3:
            st.markdown("**Author**")
            # Get available authors for this repository
            authors, author_error = data_manager.get_authors_for_repository(repo_id)
            
            if author_error:
                st.error(f"Error loading authors: {author_error}")
                author_options = []
            else:
                author_options = ["All Authors"] + sorted(authors) if authors else ["All Authors"]
            
            selected_author = st.selectbox(
                "Select Author",
                options=author_options,
                help="Filter PRs by author",
                key="lead_time_author_select"
            )
        
        # Filter control buttons
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            apply_filters = st.button("� Apply FFilters", type="primary", key="lead_time_apply_filters")
            
        with col2:
            reset_filters = st.button("🔄 Reset Filters", key="lead_time_reset_filters")
            
        # Handle reset
        if reset_filters:
            st.rerun()
        
        # Convert dates to datetime objects if provided
        start_datetime = None
        end_datetime = None
        
        if start_date:
            start_datetime = datetime.combine(start_date, datetime.min.time())
            
        if end_date:
            end_datetime = datetime.combine(end_date, datetime.max.time())
        
        # Convert author selection
        author_filter = None if selected_author == "All Authors" else selected_author
        
        # Validate filter combination
        if apply_filters and (start_datetime or end_datetime or author_filter):
            is_valid, validation_error = data_manager.validate_filter_combination(
                start_datetime, end_datetime, author_filter
            )
            
            if not is_valid:
                st.error(f"Filter validation error: {validation_error}")
                return None, None, None, False
        
        # Show active filters summary
        if apply_filters and (start_datetime or end_datetime or author_filter):
            active_filters = []
            if start_datetime:
                active_filters.append(f"Start: {start_date}")
            if end_datetime:
                active_filters.append(f"End: {end_date}")
            if author_filter:
                active_filters.append(f"Author: {author_filter}")
            
            if active_filters:
                st.info(f"Active filters: {' | '.join(active_filters)}")
        
        return start_datetime, end_datetime, author_filter, apply_filters


def display_lead_time_analysis(data_manager: DataManager, selected_repo_data: Dict[str, Any]):
    """
    Display the review lead time analysis page.
    
    Args:
        data_manager: DataManager instance for database access
        selected_repo_data: Selected repository data dictionary
        
    Requirements addressed: 1.1, 3.1, 3.2, 3.3
    """
    st.header("📊 Review Lead Time Analysis")
    st.markdown("Analyze the time it takes for pull requests to be reviewed and closed.")
    
    repo_name = f"{selected_repo_data['owner_login']}/{selected_repo_data['name']}"
    repo_id = selected_repo_data['id']
    
    st.subheader(f"Repository: {repo_name}")
    
    # Import LeadTimeAnalyzer here to avoid circular imports
    try:
        from src.analysis.lead_time_analyzer import LeadTimeAnalyzer
        analyzer = LeadTimeAnalyzer(data_manager)
        
        # Display filter UI
        start_date, end_date, author, filters_applied = display_lead_time_filters(data_manager, repo_id)
        
        # Get pull requests based on filters
        if filters_applied and (start_date or end_date or author):
            # Use filtered data
            with st.spinner("Loading filtered pull requests..."):
                all_pull_requests, pr_error_msg = data_manager.get_pull_requests_with_lead_time_data(
                    repo_id, start_date, end_date, author
                )
        else:
            # Use all pull requests
            all_pull_requests, pr_error_msg = data_manager.get_pull_requests(repo_id)
        
        if pr_error_msg:
            st.error(f"Error loading pull requests: {pr_error_msg}")
            return
            
        if not all_pull_requests:
            if filters_applied and (start_date or end_date or author):
                st.info("No pull requests match the current filter criteria.")
            else:
                st.info(f"No pull requests found for {repo_name}.")
            return
        
        # Calculate lead times
        with st.spinner("Calculating lead times..."):
            lead_time_data = analyzer.calculate_lead_times(all_pull_requests)
        
        if not lead_time_data:
            st.warning("No valid lead time data could be calculated for this repository.")
            return
        
        # Display basic metrics
        st.subheader("📈 Basic Metrics")
        
        col1, col2, col3, col4 = st.columns(4)
        
        total_prs = len(lead_time_data)
        lead_times = analyzer.get_lead_times_only(lead_time_data)
        
        if lead_times:
            avg_hours = sum(lead_times) / len(lead_times)
            min_hours = min(lead_times)
            max_hours = max(lead_times)
            median_hours = sorted(lead_times)[len(lead_times) // 2]
            
            col1.metric("Total PRs", total_prs)
            col2.metric("Average Lead Time", analyzer.format_lead_time_human_readable(avg_hours))
            col3.metric("Median Lead Time", analyzer.format_lead_time_human_readable(median_hours))
            col4.metric("Range", f"{analyzer.format_lead_time_human_readable(min_hours)} - {analyzer.format_lead_time_human_readable(max_hours)}")
        
        # Display detailed data table
        st.subheader("📋 Detailed Lead Time Data")
        
        # Prepare data for display
        display_data = []
        for pr in lead_time_data:
            display_data.append({
                "PR #": pr['pr_number'],
                "Title": pr['title'][:50] + "..." if len(pr['title']) > 50 else pr['title'],
                "Author": pr['author'],
                "Created": pr['created_at'].strftime('%Y-%m-%d %H:%M') if pr['created_at'] else 'N/A',
                "Status": pr['end_type'].title() if pr['end_type'] else 'Unknown',
                "Lead Time": analyzer.format_lead_time_human_readable(pr['lead_time_hours']),
                "Hours": f"{pr['lead_time_hours']:.1f}h"
            })
        
        st.dataframe(display_data, use_container_width=True)
        
        # Show statistics if we have enough data
        if len(lead_times) >= 3:
            st.subheader("📊 Statistical Analysis")
            
            basic_stats = analyzer.calculate_basic_statistics(lead_times)
            percentiles = analyzer.calculate_percentiles(lead_times)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Basic Statistics**")
                st.write(f"Count: {basic_stats['count']}")
                st.write(f"Mean: {analyzer.format_lead_time_human_readable(basic_stats['mean'])}")
                st.write(f"Median: {analyzer.format_lead_time_human_readable(basic_stats['median'])}")
                st.write(f"Std Dev: {basic_stats['std_dev']:.2f} hours")
            
            with col2:
                st.markdown("**Percentiles**")
                st.write(f"25th: {analyzer.format_lead_time_human_readable(percentiles['p25'])}")
                st.write(f"75th: {analyzer.format_lead_time_human_readable(percentiles['p75'])}")
                st.write(f"90th: {analyzer.format_lead_time_human_readable(percentiles['p90'])}")
                st.write(f"IQR: {percentiles['iqr']:.2f} hours")
        else:
            st.info("Need at least 3 pull requests for detailed statistical analysis.")
            
    except ImportError as e:
        st.error(f"Error importing LeadTimeAnalyzer: {e}")
        st.error("Please ensure the analysis module is properly installed.")
    except Exception as e:
        logger.error(f"Error in lead time analysis: {e}", exc_info=True)
        st.error(f"An error occurred during lead time analysis: {e}")


def main():
    """
    Streamlitアプリケーションのメイン関数
    """
    if st is None:
        print("Streamlit is not installed. Please install it with: pip install streamlit")
        return

    # ログ設定を初期化（コンソール出力を確実にする）
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),  # コンソール出力
        ]
    )
    
    # 関連モジュールのログレベルを設定
    logging.getLogger('src.gui.data_manager').setLevel(logging.INFO)
    logging.getLogger('src.github_api.client').setLevel(logging.INFO)
    logging.getLogger('src.github_api.fetcher').setLevel(logging.INFO)
    logging.getLogger('src.db.database').setLevel(logging.INFO)

    st.set_page_config(layout="wide", page_title="GitHub PR Analysis Dashboard")
    st.title("GitHub PR Analysis Dashboard")

    try:
        data_manager = DataManager()
        logger.info("DataManagerを初期化しました")

        # Pass data_manager to display_sidebar
        # It now returns three values: list of all repos, selected name, selected data dict
        all_repos, selected_repo_name, selected_repo_data = display_sidebar(data_manager)

        if not selected_repo_name or not selected_repo_data:
            if all_repos is not None and selected_repo_name is None: # Repos loaded, but none selected by user yet
                 st.info("Select a repository from the sidebar to view details.")
            # If all_repos is None, display_sidebar already showed an error or "no repos" message.
            return

        # Add navigation tabs for different analysis types
        analysis_type = st.radio(
            "Analysis Type",
            ["PR List & Details", "Review Lead Time Analysis"],
            horizontal=True,
            key="main_analysis_type_radio"
        )
        
        if analysis_type == "Review Lead Time Analysis":
            display_lead_time_analysis(data_manager, selected_repo_data)
        else:
            # Original PR list functionality
            st.header(f"Details for {selected_repo_name}")
            repo_id = selected_repo_data['id']

            st.subheader("Pull Requests")
            all_pull_requests, pr_error_msg = data_manager.get_pull_requests(repo_id)

            if pr_error_msg:
                st.error(f"Error loading pull requests: {pr_error_msg}")
                all_pull_requests = [] # Default to empty list to prevent further errors

            if not all_pull_requests and not pr_error_msg:
                st.info(f"No pull requests found for {selected_repo_name}.")
                return

            filtered_prs = all_pull_requests # Start with all PRs
            if all_pull_requests: # Only show filters and apply them if there are PRs
                selected_states, start_date, end_date = display_pr_filters(all_pull_requests)
                filtered_prs = apply_filters(all_pull_requests, selected_states, start_date, end_date)

            if filtered_prs:
                selected_pr_data_for_details = display_pr_list_and_get_selection(filtered_prs)
                if selected_pr_data_for_details:
                    display_pr_details(selected_pr_data_for_details, data_manager)
            elif not pr_error_msg: # Filtered to zero, and no initial error loading PRs
                 st.info("No pull requests match the current filter criteria.")
            # If pr_error_msg was present, it's already shown and all_pull_requests is empty

    except ValueError as ve:
        logger.error(f"Configuration error: {ve}", exc_info=True)
        st.error(f"Configuration Error: {ve}. Please check your environment variables or config.yaml.")
    except Exception as e:
        logger.error(f"An unexpected error occurred in the application: {e}", exc_info=True)
        st.error(f"An unexpected application error occurred: {e}")
        st.error("Please check the logs for more details. Ensure the database is accessible and configured correctly.")

if __name__ == '__main__':
    main()