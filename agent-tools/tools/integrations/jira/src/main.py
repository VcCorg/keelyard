"""Jira Integration Tool - Main entry point and tool implementation."""

import logging
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field
import requests
from requests.auth import HTTPBasicAuth

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class JiraIssue(BaseModel):
    """Jira issue model."""
    id: str
    key: str
    summary: str
    description: Optional[str] = None
    status: str
    priority: Optional[str] = None
    assignee: Optional[str] = None
    reporter: Optional[str] = None
    created: Optional[str] = None
    updated: Optional[str] = None
    issue_type: str
    project_key: str


class JiraProject(BaseModel):
    """Jira project model."""
    key: str
    name: str
    description: Optional[str] = None
    lead: Optional[str] = None
    issue_types: List[str] = []
    statuses: List[str] = []


class JiraIntegrationTool:
    """Tool for integrating with Jira for issue tracking and project management."""
    
    def __init__(self, base_url: str, username: str, api_token: str):
        """Initialize the Jira integration tool.
        
        Args:
            base_url: Jira base URL (e.g., https://your-domain.atlassian.net)
            username: Jira username or email
            api_token: Jira API token
        """
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.api_token = api_token
        self.auth = HTTPBasicAuth(username, api_token)
        self.session = requests.Session()
        self.session.auth = self.auth
        self.session.headers.update({
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
    
    def test_connection(self) -> Dict[str, Any]:
        """Test connection to Jira.
        
        Returns:
            Connection test result
        """
        try:
            response = self.session.get(f"{self.base_url}/rest/api/3/myself")
            if response.status_code == 200:
                user_data = response.json()
                return {
                    "success": True,
                    "message": "Connection successful",
                    "user": {
                        "displayName": user_data.get("displayName"),
                        "email": user_data.get("emailAddress"),
                        "accountId": user_data.get("accountId")
                    }
                }
            else:
                return {
                    "success": False,
                    "message": f"Connection failed: {response.status_code}",
                    "error": response.text
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"Connection error: {str(e)}"
            }
    
    def get_projects(self) -> List[JiraProject]:
        """Get all Jira projects.
        
        Returns:
            List of Jira projects
        """
        try:
            response = self.session.get(f"{self.base_url}/rest/api/3/project")
            response.raise_for_status()
            
            projects = []
            for project_data in response.json():
                project = JiraProject(
                    key=project_data.get("key"),
                    name=project_data.get("name"),
                    description=project_data.get("description"),
                    lead=project_data.get("lead", {}).get("displayName"),
                    issue_types=[it.get("name") for it in project_data.get("issueTypes", [])],
                    statuses=[]
                )
                projects.append(project)
            
            return projects
            
        except Exception as e:
            logger.error(f"Error getting projects: {e}")
            raise
    
    def get_project(self, project_key: str) -> Optional[JiraProject]:
        """Get a specific Jira project.
        
        Args:
            project_key: Project key
            
        Returns:
            Jira project or None if not found
        """
        try:
            response = self.session.get(f"{self.base_url}/rest/api/3/project/{project_key}")
            if response.status_code == 404:
                return None
            
            response.raise_for_status()
            project_data = response.json()
            
            return JiraProject(
                key=project_data.get("key"),
                name=project_data.get("name"),
                description=project_data.get("description"),
                lead=project_data.get("lead", {}).get("displayName"),
                issue_types=[it.get("name") for it in project_data.get("issueTypes", [])],
                statuses=[]
            )
            
        except Exception as e:
            logger.error(f"Error getting project {project_key}: {e}")
            raise
    
    def search_issues(self, jql: str, max_results: int = 50) -> List[JiraIssue]:
        """Search for issues using JQL.
        
        Args:
            jql: JQL query string
            max_results: Maximum number of results
            
        Returns:
            List of Jira issues
        """
        try:
            url = f"{self.base_url}/rest/api/3/search"
            params = {
                "jql": jql,
                "maxResults": max_results,
                "fields": "summary,description,status,priority,assignee,reporter,created,updated,issuetype,project"
            }
            
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            issues = []
            for issue_data in response.json().get("issues", []):
                fields = issue_data.get("fields", {})
                
                issue = JiraIssue(
                    id=issue_data.get("id"),
                    key=issue_data.get("key"),
                    summary=fields.get("summary"),
                    description=fields.get("description"),
                    status=fields.get("status", {}).get("name"),
                    priority=fields.get("priority", {}).get("name"),
                    assignee=fields.get("assignee", {}).get("displayName"),
                    reporter=fields.get("reporter", {}).get("displayName"),
                    created=fields.get("created"),
                    updated=fields.get("updated"),
                    issue_type=fields.get("issuetype", {}).get("name"),
                    project_key=fields.get("project", {}).get("key")
                )
                issues.append(issue)
            
            return issues
            
        except Exception as e:
            logger.error(f"Error searching issues: {e}")
            raise
    
    def get_issue(self, issue_key: str) -> Optional[JiraIssue]:
        """Get a specific issue.
        
        Args:
            issue_key: Issue key
            
        Returns:
            Jira issue or None if not found
        """
        try:
            response = self.session.get(f"{self.base_url}/rest/api/3/issue/{issue_key}")
            if response.status_code == 404:
                return None
            
            response.raise_for_status()
            issue_data = response.json()
            fields = issue_data.get("fields", {})
            
            return JiraIssue(
                id=issue_data.get("id"),
                key=issue_data.get("key"),
                summary=fields.get("summary"),
                description=fields.get("description"),
                status=fields.get("status", {}).get("name"),
                priority=fields.get("priority", {}).get("name"),
                assignee=fields.get("assignee", {}).get("displayName"),
                reporter=fields.get("reporter", {}).get("displayName"),
                created=fields.get("created"),
                updated=fields.get("updated"),
                issue_type=fields.get("issuetype", {}).get("name"),
                project_key=fields.get("project", {}).get("key")
            )
            
        except Exception as e:
            logger.error(f"Error getting issue {issue_key}: {e}")
            raise
    
    def create_issue(
        self,
        project_key: str,
        summary: str,
        issue_type: str,
        description: Optional[str] = None,
        priority: Optional[str] = None,
        assignee: Optional[str] = None
    ) -> JiraIssue:
        """Create a new issue.
        
        Args:
            project_key: Project key
            summary: Issue summary
            issue_type: Issue type name
            description: Issue description
            priority: Priority name
            assignee: Assignee username
            
        Returns:
            Created Jira issue
        """
        try:
            issue_data = {
                "fields": {
                    "project": {"key": project_key},
                    "summary": summary,
                    "issuetype": {"name": issue_type}
                }
            }
            
            if description:
                issue_data["fields"]["description"] = description
            
            if priority:
                issue_data["fields"]["priority"] = {"name": priority}
            
            if assignee:
                issue_data["fields"]["assignee"] = {"name": assignee}
            
            response = self.session.post(
                f"{self.base_url}/rest/api/3/issue",
                json=issue_data
            )
            response.raise_for_status()
            
            created_issue = response.json()
            return self.get_issue(created_issue.get("key"))
            
        except Exception as e:
            logger.error(f"Error creating issue: {e}")
            raise
    
    def add_comment(self, issue_key: str, comment: str) -> bool:
        """Add a comment to an issue.
        
        Args:
            issue_key: Issue key
            comment: Comment text
            
        Returns:
            True if successful
        """
        try:
            comment_data = {
                "body": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [
                                {
                                    "type": "text",
                                    "text": comment
                                }
                            ]
                        }
                    ]
                }
            }
            
            response = self.session.post(
                f"{self.base_url}/rest/api/3/issue/{issue_key}/comment",
                json=comment_data
            )
            response.raise_for_status()
            
            return True
            
        except Exception as e:
            logger.error(f"Error adding comment to {issue_key}: {e}")
            return False
    
    def transition_issue(self, issue_key: str, transition_name: str) -> bool:
        """Transition an issue to a new status.
        
        Args:
            issue_key: Issue key
            transition_name: Transition name
            
        Returns:
            True if successful
        """
        try:
            # Get available transitions
            response = self.session.get(f"{self.base_url}/rest/api/3/issue/{issue_key}/transitions")
            response.raise_for_status()
            
            transitions = response.json().get("transitions", [])
            transition_id = None
            
            for transition in transitions:
                if transition.get("name", "").lower() == transition_name.lower():
                    transition_id = transition.get("id")
                    break
            
            if not transition_id:
                logger.error(f"Transition '{transition_name}' not found for issue {issue_key}")
                return False
            
            # Perform transition
            transition_data = {
                "transition": {
                    "id": transition_id
                }
            }
            
            response = self.session.post(
                f"{self.base_url}/rest/api/3/issue/{issue_key}/transitions",
                json=transition_data
            )
            response.raise_for_status()
            
            return True
            
        except Exception as e:
            logger.error(f"Error transitioning issue {issue_key}: {e}")
            return False
    
    def get_my_issues(self, status: Optional[str] = None) -> List[JiraIssue]:
        """Get issues assigned to the current user.
        
        Args:
            status: Filter by status
            
        Returns:
            List of Jira issues
        """
        jql = f"assignee = currentUser()"
        if status:
            jql += f" AND status = '{status}'"
        
        return self.search_issues(jql)
    
    def get_tool_info(self) -> Dict[str, Any]:
        """Get tool information and capabilities.
        
        Returns:
            Tool information
        """
        return {
            "name": "Jira Integration Tool",
            "version": "1.1.0",
            "description": "Tool for integrating with Jira for issue tracking and project management",
            "capabilities": [
                "test_connection",
                "get_projects",
                "get_project",
                "search_issues",
                "get_issue",
                "create_issue",
                "add_comment",
                "transition_issue",
                "get_my_issues"
            ],
            "dependencies": ["jira>=3.1.0", "requests>=2.31.0", "pydantic>=2.0.0"],
            "author": "KEEL Team"
        }


# Example usage
if __name__ == "__main__":
    # This would typically be configured through environment variables or config
    import os
    
    # Example configuration
    JIRA_URL = os.getenv("JIRA_URL", "https://your-domain.atlassian.net")
    JIRA_USERNAME = os.getenv("JIRA_USERNAME", "your-email@example.com")
    JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN", "your-api-token")
    
    if all([JIRA_URL, JIRA_USERNAME, JIRA_API_TOKEN]):
        tool = JiraIntegrationTool(JIRA_URL, JIRA_USERNAME, JIRA_API_TOKEN)
        
        # Test connection
        result = tool.test_connection()
        print(f"Connection test: {result}")
        
        if result["success"]:
            # Get projects
            projects = tool.get_projects()
            print(f"Found {len(projects)} projects")
            
            # Get my issues
            my_issues = tool.get_my_issues()
            print(f"Found {len(my_issues)} issues assigned to me")
    else:
        print("Please set JIRA_URL, JIRA_USERNAME, and JIRA_API_TOKEN environment variables")
