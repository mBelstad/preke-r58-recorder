"""
Apply project template to DaVinci Resolve project.

Templates can include pre-configured settings, timelines, and effects.
"""

import sys
import os
from pathlib import Path

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


def apply_template(project_name: str, template_path: str) -> bool:
    """Apply a project template to an existing project.
    
    Args:
        project_name: Name of target DaVinci Resolve project
        template_path: Path to template .drp file or template project name
    
    Returns:
        True if successful, False otherwise
    
    Note: Template application in DaVinci Resolve typically involves:
    1. Loading a template project (.drp file)
    2. Copying settings, timelines, or effects
    3. Applying to target project
    
    This is a placeholder implementation.
    """
    resolve = dvr_script.scriptapp("Resolve")
    if not resolve:
        print("Error: DaVinci Resolve not available")
        return False
    
    project_manager = resolve.GetProjectManager()
    project = project_manager.LoadProject(project_name)
    
    if not project:
        print(f"Error: Project {project_name} not found")
        return False
    
    # Check if template is a file path or project name
    template_file = Path(template_path)
    if template_file.exists() and template_file.suffix == '.drp':
        # Load template project
        template_project = project_manager.LoadProject(str(template_file))
        if not template_project:
            print(f"Error: Failed to load template from {template_path}")
            return False
        
        print(f"Loaded template from {template_path}")
        # TODO: Copy settings/timelines from template_project to project
        print("Template loaded - settings copy not yet implemented")
        
    else:
        # Assume template is a project name in database
        template_project = project_manager.LoadProject(template_path)
        if not template_project:
            print(f"Error: Template project {template_path} not found")
            return False
        
        print(f"Loaded template project: {template_path}")
        # TODO: Copy settings/timelines from template_project to project
        print("Template loaded - settings copy not yet implemented")
    
    return True


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: apply_template.py <project_name> <template_path_or_name>")
        print("  template_path_or_name: Path to .drp file or name of template project")
        print("Example: apply_template.py session_20250108_143022 /path/to/template.drp")
        print("Example: apply_template.py session_20250108_143022 multicam_template")
        sys.exit(1)
    
    project_name = sys.argv[1]
    template_path = sys.argv[2]
    
    success = apply_template(project_name, template_path)
    sys.exit(0 if success else 1)
