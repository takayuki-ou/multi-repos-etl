"""
Streamlit GUI for GitHub PR Analysis Dashboard
"""
import streamlit as st
from src.gui.data_manager import DataManager
import logging
from datetime import datetime

# ロギングの設定
logger = logging.getLogger(__name__)

# Helper functions for Streamlit UI elements
def display_sidebar(data_manager: DataManager) -> tuple[Optional[list[dict]], Optional[str], Optional[dict]]:
    """Displays the sidebar for repository selection and returns selected repo info."""
    st.sidebar.header("Repositories")
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


def display_pr_filters(all_pull_requests: list[dict]) -> tuple[list[str], Optional[datetime.date], Optional[datetime.date]]:
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
    all_pull_requests: list[dict],
    selected_states: list[str],
    start_date: Optional[datetime.date],
    end_date: Optional[datetime.date]
) -> list[dict]:
    """Applies filters to the list of pull requests."""
    filtered_prs = all_pull_requests
    if selected_states:
        filtered_prs = [pr for pr in filtered_prs if pr.get('state') in selected_states]
    if start_date:
        filtered_prs = [pr for pr in filtered_prs if pr.get('created_at_dt') and pr['created_at_dt'].date() >= start_date]
    if end_date:
        filtered_prs = [pr for pr in filtered_prs if pr.get('created_at_dt') and pr['created_at_dt'].date() <= end_date]
    return filtered_prs


def display_pr_list_and_get_selection(filtered_prs: list[dict]) -> Optional[dict]:
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


def display_pr_details(selected_pr_data: dict, data_manager: DataManager):
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


def main():
    """
    Streamlitアプリケーションのメイン関数
    """
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
