"""
Environment Setup Script for AgoraProf LMS

This script sets up the virtual environment, installs requirements,
and starts the Django development server.
"""

import os
import sys
import subprocess
import venv

def run_command(command, cwd=None):
    """Run a command and return the result"""
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True
        )
        return True, result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        return False, e.stdout, e.stderr

def main():
    """Main setup function"""
    project_root = os.path.dirname(os.path.abspath(__file__))
    venv_path = os.path.join(project_root, 'venv')
    
    print("🚀 AGORAPROF LMS - Environment Setup")
    print("=" * 50)
    
    # Step 1: Create virtual environment
    print("\n📦 Step 1: Creating virtual environment...")
    if not os.path.exists(venv_path):
        success, stdout, stderr = run_command(f'python -m venv "{venv_path}"', cwd=project_root)
        if success:
            print("✅ Virtual environment created successfully")
        else:
            print(f"❌ Failed to create virtual environment: {stderr}")
            return False
    else:
        print("✅ Virtual environment already exists")
    
    # Determine activation script path
    if sys.platform == "win32":
        activate_script = os.path.join(venv_path, 'Scripts', 'activate.bat')
        python_executable = os.path.join(venv_path, 'Scripts', 'python.exe')
        pip_executable = os.path.join(venv_path, 'Scripts', 'pip.exe')
    else:
        activate_script = os.path.join(venv_path, 'bin', 'activate')
        python_executable = os.path.join(venv_path, 'bin', 'python')
        pip_executable = os.path.join(venv_path, 'bin', 'pip')
    
    # Step 2: Upgrade pip
    print("\n⬆️  Step 2: Upgrading pip...")
    success, stdout, stderr = run_command(f'"{pip_executable}" install --upgrade pip', cwd=project_root)
    if success:
        print("✅ Pip upgraded successfully")
    else:
        print(f"⚠️  Pip upgrade warning: {stderr}")
    
    # Step 3: Install requirements
    print("\n📚 Step 3: Installing requirements...")
    requirements_file = os.path.join(project_root, 'requirements.txt')
    
    if os.path.exists(requirements_file):
        success, stdout, stderr = run_command(f'"{pip_executable}" install -r "{requirements_file}"', cwd=project_root)
        if success:
            print("✅ Requirements installed successfully")
        else:
            print(f"❌ Failed to install requirements: {stderr}")
            return False
    else:
        print("❌ requirements.txt not found")
        return False
    
    # Step 4: Run Django migrations
    print("\n🗄️  Step 4: Running Django migrations...")
    manage_py = os.path.join(project_root, 'manage.py')
    
    success, stdout, stderr = run_command(f'"{python_executable}" "{manage_py}" migrate', cwd=project_root)
    if success:
        print("✅ Migrations completed successfully")
    else:
        print(f"❌ Migration failed: {stderr}")
        return False
    
    # Step 5: Create superuser (optional)
    print("\n👤 Step 5: Creating superuser (optional)...")
    success, stdout, stderr = run_command(f'"{python_executable}" "{manage_py}" createsuperuser --noinput --username admin --email admin@agoraprof.com', cwd=project_root)
    if success:
        print("✅ Superuser created successfully")
    else:
        print("ℹ️  Superuser already exists or creation failed (you can create manually)")
    
    # Step 6: Collect static files
    print("\n📁 Step 6: Collecting static files...")
    success, stdout, stderr = run_command(f'"{python_executable}" "{manage_py}" collectstatic --noinput', cwd=project_root)
    if success:
        print("✅ Static files collected successfully")
    else:
        print(f"⚠️  Static files collection warning: {stderr}")
    
    # Step 7: Start development server
    print("\n🚀 Step 7: Starting Django development server...")
    print("=" * 50)
    print("🌐 Server will be available at: http://127.0.0.1:8000")
    print("🌐 Alternative URL: http://localhost:8000")
    print("🛑 Press Ctrl+C to stop the server")
    print("=" * 50)
    
    # Start the server
    try:
        subprocess.run(
            [python_executable, manage_py, 'runserver', '0.0.0.0:8000'],
            cwd=project_root
        )
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Failed to start server: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    if success:
        print("\n🎉 Setup completed successfully!")
    else:
        print("\n❌ Setup failed. Please check the errors above.")
        sys.exit(1)
