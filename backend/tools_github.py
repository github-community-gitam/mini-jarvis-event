from github import Github
from integrations import get_integration_token
from tool_registry import registry

def get_github_client():
    token_data = get_integration_token("github")
    if not token_data:
        raise Exception("GitHub is not connected. Please connect it in the Integrations panel.")
    return Github(token_data['access_token'])

def list_repositories(limit: int = 10):
    """List repositories for the authenticated user"""
    try:
        g = get_github_client()
        user = g.get_user()
        repos = user.get_repos(sort="updated", direction="desc")
        
        result = []
        for i, repo in enumerate(repos):
            if i >= limit:
                break
            result.append(f"- {repo.full_name}: {repo.description or 'No description'} (Stars: {repo.stargazers_count})")
        
        if not result:
            return "No repositories found."
        return "\n".join(result)
    except Exception as e:
        return f"Error listing repositories: {str(e)}"

def get_repository_info(repo_name: str):
    """Retrieve detailed information about a specific repository (e.g., 'ramkolipakula/mini-jarvis')"""
    try:
        g = get_github_client()
        repo = g.get_repo(repo_name)
        
        return f"Repository: {repo.full_name}\nDescription: {repo.description}\nStars: {repo.stargazers_count}\nForks: {repo.forks_count}\nLanguage: {repo.language}\nDefault Branch: {repo.default_branch}"
    except Exception as e:
        return f"Error fetching repository info: {str(e)}"

def list_open_issues(repo_name: str, limit: int = 5):
    """List open issues for a specific repository"""
    try:
        g = get_github_client()
        repo = g.get_repo(repo_name)
        issues = repo.get_issues(state="open")
        
        result = []
        for i, issue in enumerate(issues):
            if i >= limit:
                break
            # get_issues returns pull requests as well in PyGithub, filter them out if needed
            if issue.pull_request is None:
                result.append(f"#{issue.number} - {issue.title} (by {issue.user.login})")
                
        if not result:
            return f"No open issues found in {repo_name}."
        return "\n".join(result)
    except Exception as e:
        return f"Error listing issues: {str(e)}"

def get_recent_commits(repo_name: str, branch: str = None, limit: int = 5):
    """Retrieve recent commits for a specific repository"""
    try:
        g = get_github_client()
        repo = g.get_repo(repo_name)
        
        kwargs = {}
        if branch:
            kwargs["sha"] = branch
            
        commits = repo.get_commits(**kwargs)
        
        result = []
        for i, commit in enumerate(commits):
            if i >= limit:
                break
            result.append(f"- [{commit.sha[:7]}] {commit.commit.message.splitlines()[0]} (by {commit.commit.author.name})")
            
        if not result:
            return "No commits found."
        return "\n".join(result)
    except Exception as e:
        return f"Error fetching commits: {str(e)}"

def list_pull_requests(repo_name: str, state: str = "open", limit: int = 5):
    """Summarize pull requests for a specific repository"""
    try:
        g = get_github_client()
        repo = g.get_repo(repo_name)
        prs = repo.get_pulls(state=state, sort="created", direction="desc")
        
        result = []
        for i, pr in enumerate(prs):
            if i >= limit:
                break
            result.append(f"PR #{pr.number}: {pr.title} ({pr.state}) by {pr.user.login}")
            
        if not result:
            return f"No {state} pull requests found in {repo_name}."
        return "\n".join(result)
    except Exception as e:
        return f"Error fetching pull requests: {str(e)}"

# Register Tools

registry.register(
    name="list_github_repositories",
    description="List the GitHub repositories accessible to the user.",
    parameters={
        "type": "object",
        "properties": {
            "limit": {
                "type": "integer",
                "description": "Maximum number of repositories to return. Default 10."
            }
        }
    },
    func=list_repositories,
    requires_confirmation=False
)

registry.register(
    name="get_github_repository_info",
    description="Get basic information about a specific GitHub repository.",
    parameters={
        "type": "object",
        "properties": {
            "repo_name": {
                "type": "string",
                "description": "The full name of the repository (e.g., 'owner/repo')."
            }
        },
        "required": ["repo_name"]
    },
    func=get_repository_info,
    requires_confirmation=False
)

registry.register(
    name="list_github_issues",
    description="List open issues in a specific GitHub repository.",
    parameters={
        "type": "object",
        "properties": {
            "repo_name": {
                "type": "string",
                "description": "The full name of the repository."
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of issues to return. Default 5."
            }
        },
        "required": ["repo_name"]
    },
    func=list_open_issues,
    requires_confirmation=False
)

registry.register(
    name="get_github_commits",
    description="Get recent commits from a specific GitHub repository.",
    parameters={
        "type": "object",
        "properties": {
            "repo_name": {
                "type": "string",
                "description": "The full name of the repository."
            },
            "branch": {
                "type": "string",
                "description": "The branch name to fetch commits from (optional)."
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of commits to return. Default 5."
            }
        },
        "required": ["repo_name"]
    },
    func=get_recent_commits,
    requires_confirmation=False
)

registry.register(
    name="list_github_pull_requests",
    description="List pull requests for a specific GitHub repository.",
    parameters={
        "type": "object",
        "properties": {
            "repo_name": {
                "type": "string",
                "description": "The full name of the repository."
            },
            "state": {
                "type": "string",
                "description": "State of the pull requests to fetch ('open', 'closed', 'all'). Default 'open'."
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of pull requests to return. Default 5."
            }
        },
        "required": ["repo_name"]
    },
    func=list_pull_requests,
    requires_confirmation=False
)
