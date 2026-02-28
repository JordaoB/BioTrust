"""
Quick System Test - BioTrust
Testa rapidamente se todos os componentes estão funcionando.
"""

import sys
import importlib

def test_imports():
    """Test if all required packages are installed"""
    print("=" * 60)
    print("🧪 BioTrust - System Test")
    print("=" * 60)
    print()
    
    packages = {
        'cv2': 'opencv-python',
        'mediapipe': 'mediapipe',
        'numpy': 'numpy',
        'scipy': 'scipy',
        'colorama': 'colorama',
        'fastapi': 'fastapi',
        'uvicorn': 'uvicorn',
        'streamlit': 'streamlit',
        'requests': 'requests',
        'pydantic': 'pydantic'
    }
    
    print("📦 Checking dependencies...")
    print()
    
    all_ok = True
    for package, pip_name in packages.items():
        try:
            importlib.import_module(package)
            print(f"  ✅ {pip_name}")
        except ImportError:
            print(f"  ❌ {pip_name} - NOT INSTALLED")
            all_ok = False
    
    print()
    
    if not all_ok:
        print("❌ Some packages are missing!")
        print()
        print("Install with:")
        print("  pip install -r requirements.txt")
        print()
        return False
    
    print("✅ All dependencies installed!")
    print()
    return True

def test_modules():
    """Test if all BioTrust modules can be imported"""
    print("📁 Checking BioTrust modules...")
    print()
    
    modules = [
        'risk_engine',
        'liveness_detector',
        'passive_liveness',
        'transaction_logger',
        'api_server',
        'web_app'
    ]
    
    all_ok = True
    for module in modules:
        try:
            importlib.import_module(module)
            print(f"  ✅ {module}.py")
        except Exception as e:
            print(f"  ❌ {module}.py - Error: {str(e)[:50]}")
            all_ok = False
    
    print()
    
    if not all_ok:
        print("⚠️ Some modules have issues!")
        print()
        return False
    
    print("✅ All modules OK!")
    print()
    return True

def test_camera():
    """Test if camera is accessible"""
    print("📸 Checking camera access...")
    print()
    
    try:
        import cv2
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            ret, frame = cap.read()
            cap.release()
            if ret:
                print("  ✅ Camera working!")
                print()
                return True
            else:
                print("  ⚠️ Camera opened but couldn't read frame")
                print()
                return False
        else:
            print("  ❌ Camera not accessible")
            print("     - Check camera permissions")
            print("     - Close other apps using camera")
            print()
            return False
    except Exception as e:
        print(f"  ❌ Camera error: {str(e)}")
        print()
        return False

def print_next_steps():
    """Print instructions for next steps"""
    print("=" * 60)
    print("🚀 Next Steps")
    print("=" * 60)
    print()
    print("Option 1: Start everything automatically")
    print("  > start_all.bat")
    print()
    print("Option 2: Start API server")
    print("  > .\\venv310\\Scripts\\python.exe api_server.py")
    print("  Then visit: http://localhost:8000/docs")
    print()
    print("Option 3: Start Streamlit (API must be running)")
    print("  > .\\venv310\\Scripts\\streamlit run web_app.py")
    print("  Then visit: http://localhost:8501")
    print()
    print("Option 4: Test liveness detection")
    print("  > .\\venv310\\Scripts\\python.exe test_integrated_liveness.py")
    print()
    print("Option 5: Demo for judges")
    print("  > .\\venv310\\Scripts\\python.exe demo_liveness.py")
    print()

def main():
    """Run all tests"""
    deps_ok = test_imports()
    
    if not deps_ok:
        print("Fix dependencies first, then run this test again.")
        sys.exit(1)
    
    modules_ok = test_modules()
    camera_ok = test_camera()
    
    print("=" * 60)
    print("📊 Test Summary")
    print("=" * 60)
    print()
    print(f"  Dependencies: {'✅ PASS' if deps_ok else '❌ FAIL'}")
    print(f"  Modules:      {'✅ PASS' if modules_ok else '❌ FAIL'}")
    print(f"  Camera:       {'✅ PASS' if camera_ok else '⚠️  WARNING'}")
    print()
    
    if deps_ok and modules_ok:
        print("✅ System is ready!")
        if not camera_ok:
            print("⚠️  Camera issues detected - liveness detection may not work")
        print()
        print_next_steps()
        return 0
    else:
        print("❌ System has issues - please fix them first")
        return 1

if __name__ == "__main__":
    sys.exit(main())
