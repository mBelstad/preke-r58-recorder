"""
Create DaVinci Resolve project for a recording session.

This script can be called directly or imported by the automation service.
"""

import sys
import os

# Add DaVinci Resolve Scripting API to path
if sys.platform == "darwin":
    resolve_api_path = "/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/Modules"
elif sys.platform == "win32":
    resolve_api_path = r"C:\ProgramData\Blackmagic Design\DaVinci Resolve\Support\Developer\Scripting\Modules"
else:
    resolve_api_path = "/opt/resolve/Developer/Scripting/Modules"

if os.path.exists(resolve_api_path):
    sys.path.insert(0, resolve_api_path)

try:
    import DaVinciResolveScript as dvr_script
except ImportError:
    print("Error: Could not import DaVinciResolveScript")
    sys.exit(1)


def create_project(session_id: str, template_name: str = None) -> bool:
    """Create a new DaVinci Resolve project.
    
    Args:
        session_id: Unique session identifier (used as project name)
        template_name: Optional template to apply
        
    Returns:
        True if successful, False otherwise
    """
    resolve = dvr_script.scriptapp("Resolve")
    if not resolve:
        print("Error: DaVinci Resolve not available")
        return False
    
    project_manager = resolve.GetProjectManager()
    
    # Check if project already exists
    existing_project = project_manager.LoadProject(session_id)
    if existing_project:
        print(f"Project {session_id} already exists")
        return True
    
    # Create new project
    project = project_manager.CreateProject(session_id)
    if not project:
        print(f"Failed to create project {session_id}")
        return False
    
    print(f"Created project: {session_id}")
    
    # Apply template if specified
    if template_name:
        apply_template(project, template_name)
    
    return True


def apply_template(project, template_name: str):
    """Apply a project template.
    
    Args:
        project: DaVinci Resolve project object
        template_name: Name of template to apply
        
    Note: Template loading requires DaVinci Resolve project templates
    to be saved in the appropriate location. This is a placeholder
    for future implementation.
    """
    # TODO: Implement template loading
    # Templates are typically saved as .drp files
    # Can be loaded via project_manager.LoadProject(template_path)
    print(f"Template {template_name} would be applied (not yet implemented)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: create_session_project.py <session_id> [template_name]")
        sys.exit(1)
    
    session_id = sys.argv[1]
    template = sys.argv[2] if len(sys.argv) > 2 else None
    
    success = create_project(session_id, template)
    sys.exit(0 if success else 1)
