#!/usr/bin/env python
"""
Simple dependency installer for the Crawler project.
Installs required packages, Playwright browsers, and system dependencies.
"""

import subprocess
import sys
import os
import platform

def main():
    print("Setting up the Crawler environment...")
    
    # Step 1: Install Python dependencies
    print("\n[1/3] Installing Python dependencies...")
    requirements_file = os.path.join(os.path.dirname(__file__), "requirements.txt")
    
    if os.path.exists(requirements_file):
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", requirements_file])
    else:
        print(f"Warning: requirements.txt not found at {requirements_file}")
        # Install core dependencies
        subprocess.check_call([sys.executable, "-m", "pip", "install", "crawl4ai", "openai", "fastapi", "uvicorn", "beautifulsoup4", "requests", "python-dotenv"])
    
    # Step 2: Install Playwright browsers
    print("\n[2/3] Installing Playwright browsers...")
    try:
        subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])
        print("Playwright browsers successfully installed!")
    except subprocess.CalledProcessError as e:
        print(f"Error installing Playwright browsers: {e}")
        print("You may need to run 'playwright install' manually.")
        return False
    
    # Step 3: Install system dependencies for Playwright
    print("\n[3/3] Installing system dependencies for Playwright...")
    
    # Check if we're on Linux
    if platform.system() == "Linux":
        print("Detected Linux system. Installing browser dependencies...")
        
        try:
            # Try with sudo first (most common case)
            print("\nAttempting to install dependencies with sudo...")
            print("You may be prompted for your password.")
            print("Command: sudo playwright install-deps")
            
            try:
                subprocess.check_call(["sudo", "playwright", "install-deps"])
                print("✅ System dependencies installed successfully with sudo!")
            except (subprocess.CalledProcessError, FileNotFoundError):
                # If direct playwright command fails, try with python -m 
                print("\nRetrying with python module approach...")
                subprocess.check_call(["sudo", sys.executable, "-m", "playwright", "install-deps"])
                print("✅ System dependencies installed successfully with sudo!")
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print(f"\nCould not install dependencies with sudo: {e}")
            
            print("\nAlternative dependency installation methods:")
            print("\n1. Manual installation with apt:")
            print("   sudo apt-get install libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 libxcomposite1")
            print("   libxdamage1 libxfixes3 libxrandr2 libgbm1 libxkbcommon0 libpango-1.0-0 libcairo2 libasound2 libatspi2.0-0")
            
            print("\n2. Or try running with non-sudo user:")
            print(f"   {sys.executable} -m playwright install-deps")
            
            print("\nAfter installing dependencies, try running your crawler again.")
            return False
    else:
        print(f"Detected {platform.system()} system. No additional system dependencies needed.")
    
    print("\n✅ Setup completed successfully! You can now run the crawler.")
    return True

if __name__ == "__main__":
    try:
        success = main()
        if not success:
            sys.exit(1)
    except KeyboardInterrupt:
        print("\nSetup interrupted.")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error during setup: {e}")
        sys.exit(1)