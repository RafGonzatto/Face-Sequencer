# run_app_with_fix.py - Run app.py with PyTorch fixes applied

# Apply PyTorch 2.6 compatibility fix for WhisperX
try:
    import fix_pytorch_whisperx
    fix_pytorch_whisperx.monkey_patch_torch()
    print("✅ PyTorch 2.6 compatibility patch applied")
except Exception as e:
    print(f"⚠️ Warning: Could not apply PyTorch patch: {e}")

# Now import and run app.py normally
import app

# If app has a main function, call it
if __name__ == "__main__":
    # If the app has a specific entry point function, call it
    if hasattr(app, "main"):
        app.main()