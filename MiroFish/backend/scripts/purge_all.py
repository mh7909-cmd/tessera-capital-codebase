import os
import sys
import shutil

# Ensure we can import from app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.config import Config
from app.models.project import ProjectManager
from app.services.graph_builder import GraphBuilderService

def purge_all():
    print("🧹 Starting Global Purge...")
    
    # 1. Initialize Zep Service
    if not Config.ZEP_API_KEY:
        print("❌ Error: ZEP_API_KEY not found in config.")
        return
    
    builder = GraphBuilderService(api_key=Config.ZEP_API_KEY)
    
    # 2. Get all local projects
    projects = ProjectManager.list_projects(limit=1000)
    print(f"📦 Found {len(projects)} local projects.")
    
    # 3. Delete Zep Graphs and Local Data
    for project in projects:
        p_id = project.project_id
        g_id = project.graph_id
        
        if g_id:
            print(f"  🗑️ Deleting Zep Graph: {g_id} (Project: {p_id})")
            try:
                builder.delete_graph(g_id)
            except Exception as e:
                print(f"    ⚠️ Failed to delete Zep graph {g_id}: {e}")
        
        print(f"  🗑️ Deleting Local Project: {p_id}")
        ProjectManager.delete_project(p_id)

    # 4. Final Cleanup of the projects directory if anything remains
    projects_dir = os.path.join(Config.UPLOAD_FOLDER, 'projects')
    if os.path.exists(projects_dir):
        print(f"  🗑️ Purging remains in {projects_dir}...")
        for item in os.listdir(projects_dir):
            item_path = os.path.join(projects_dir, item)
            try:
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                else:
                    os.remove(item_path)
            except Exception as e:
                print(f"    ⚠️ Failed to remove {item}: {e}")

    # 5. Cleanup simulations folder
    sim_dir = Config.OASIS_SIMULATION_DATA_DIR
    if os.path.exists(sim_dir):
        print(f"  🗑️ Purging simulations in {sim_dir}...")
        try:
            shutil.rmtree(sim_dir)
            os.makedirs(sim_dir, exist_ok=True)
        except Exception as e:
            print(f"    ⚠️ Failed to purge simulations: {e}")

    print("\n✅ GLOBAL PURGE COMPLETE. System is fresh.")

if __name__ == "__main__":
    purge_all()
