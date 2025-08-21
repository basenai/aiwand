import os
import sys

# Force unbuffered output for reliability in CI/logging
sys.stdout.reconfigure(line_buffering=True)

try:
    from PyQt5 import QtCore, QtWidgets
except Exception as e:
    print("PyQt5 import failed:", repr(e))
    sys.exit(2)

print("Python:", sys.version)
print("PyQt5:", getattr(QtCore, "PYQT_VERSION_STR", "unknown"))
print("Qt:", getattr(QtCore, "QT_VERSION_STR", "unknown"))

# Ensure offscreen platform, if not already set
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
print("QT_QPA_PLATFORM env:", os.environ.get("QT_QPA_PLATFORM"))

# Create or reuse application instance
try:
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    print("Created QApplication:", bool(app))
    try:
        print("app.platformName():", app.platformName())
    except Exception as e:
        print("platformName() check failed:", repr(e))

    # Show plugin search paths
    try:
        plugins_path = None
        if hasattr(QtCore.QLibraryInfo, "location"):
            plugins_path = QtCore.QLibraryInfo.location(QtCore.QLibraryInfo.PluginsPath)
        elif hasattr(QtCore.QLibraryInfo, "path"):
            plugins_path = QtCore.QLibraryInfo.path(QtCore.QLibraryInfo.PluginsPath)
        print("QLibraryInfo.pluginsPath:", plugins_path)
    except Exception as e:
        print("QLibraryInfo.pluginsPath check failed:", repr(e))

    try:
        print("QCoreApplication.libraryPaths:", QtCore.QCoreApplication.libraryPaths())
    except Exception as e:
        print("libraryPaths check failed:", repr(e))

    # Inspect platforms plugin folder and common platform plugins
    try:
        from pathlib import Path
        plat_dir = None
        if 'plugins_path' in locals() and plugins_path:
            plat_dir = Path(plugins_path) / "platforms"
            print("Platforms dir:", str(plat_dir))
            if plat_dir.exists():
                names = sorted(p.name for p in plat_dir.glob('*'))
                print("Platform plugins:", names)
                for name in ("qoffscreen", "qminimal", "qwindows"):
                    matches = list(plat_dir.glob(f"{name}.*"))
                    print(f"Has {name} plugin:", bool(matches))
            else:
                print("Platforms dir does not exist")
    except Exception as e:
        print("Platforms dir check failed:", repr(e))

    sys.exit(0)
except Exception as e:
    print("QApplication creation failed:", repr(e))
    sys.exit(3)
