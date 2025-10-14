#!/usr/bin/env python3
"""
Smart Project Clone Script
Project Creator: Herman Swanepoel
Version: 1.0
Date: 2025-10-14

Intelligently clones project files, skipping files that already exist with content.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
import hashlib


class SmartCloner:
    def __init__(self, repo_url, target_dir="."):
        self.repo_url = repo_url
        self.target_dir = Path(target_dir).resolve()
        self.temp_dir = self.target_dir / ".temp_clone"
        self.skipped_files = []
        self.cloned_files = []
        self.errors = []

    def file_has_content(self, filepath):
        """Check if file exists and has content"""
        if not filepath.exists():
            return False
        try:
            return filepath.stat().st_size > 0
        except:
            return False

    def files_are_identical(self, file1, file2):
        """Compare two files using hash"""
        try:
            hash1 = hashlib.md5(file1.read_bytes()).hexdigest()
            hash2 = hashlib.md5(file2.read_bytes()).hexdigest()
            return hash1 == hash2
        except:
            return False

    def clone_repository(self):
        """Clone repository to temporary directory"""
        print(f"🔄 Cloning repository from {self.repo_url}...")
        try:
            subprocess.run(
                ["git", "clone", self.repo_url, str(self.temp_dir)], check=True, capture_output=True
            )
            print("✅ Repository cloned to temporary directory")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to clone repository: {e.stderr.decode()}")
            return False

    def smart_copy(self, src, dst):
        """Intelligently copy file or directory"""
        if src.is_file():
            # Check if destination file exists with content
            if self.file_has_content(dst):
                # Check if files are identical
                if self.files_are_identical(src, dst):
                    self.skipped_files.append(str(dst.relative_to(self.target_dir)))
                    return "identical"
                else:
                    self.skipped_files.append(str(dst.relative_to(self.target_dir)))
                    return "exists"

            # Copy the file
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            self.cloned_files.append(str(dst.relative_to(self.target_dir)))
            return "copied"

        elif src.is_dir():
            # Skip .git directory
            if src.name == ".git":
                return "skipped_git"

            # Create directory if it doesn't exist
            dst.mkdir(parents=True, exist_ok=True)

            # Recursively copy contents
            for item in src.iterdir():
                self.smart_copy(item, dst / item.name)

            return "directory"

    def sync_files(self):
        """Sync files from temp directory to target"""
        print("\n📦 Syncing files...")

        for item in self.temp_dir.iterdir():
            if item.name == ".git":
                continue

            target_path = self.target_dir / item.name
            result = self.smart_copy(item, target_path)

    def cleanup(self):
        """Remove temporary directory"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
            print("\n🧹 Cleaned up temporary files")

    def print_summary(self):
        """Print operation summary"""
        print("\n" + "=" * 60)
        print("📊 SMART CLONE SUMMARY")
        print("=" * 60)

        print(f"\n✅ Files Cloned: {len(self.cloned_files)}")
        if self.cloned_files:
            for f in self.cloned_files[:10]:
                print(f"   • {f}")
            if len(self.cloned_files) > 10:
                print(f"   ... and {len(self.cloned_files) - 10} more")

        print(f"\n⏭️  Files Skipped (already exist): {len(self.skipped_files)}")
        if self.skipped_files:
            for f in self.skipped_files[:10]:
                print(f"   • {f}")
            if len(self.skipped_files) > 10:
                print(f"   ... and {len(self.skipped_files) - 10} more")

        if self.errors:
            print(f"\n⚠️  Errors: {len(self.errors)}")
            for e in self.errors:
                print(f"   • {e}")

        print("\n" + "=" * 60)
        print("✨ Smart clone completed!")
        print("=" * 60)

    def run(self):
        """Execute smart clone process"""
        print("🚀 Starting Smart Clone Process")
        print(f"📁 Target Directory: {self.target_dir}")

        try:
            # Clone repository
            if not self.clone_repository():
                return False

            # Sync files intelligently
            self.sync_files()

            # Print summary
            self.print_summary()

            return True

        except Exception as e:
            print(f"\n❌ Error during clone process: {e}")
            return False

        finally:
            # Always cleanup
            self.cleanup()


def main():
    """Main entry point"""
    print(
        """
╔═══════════════════════════════════════════════════════════╗
║         SMART PROJECT CLONE SCRIPT v1.0                   ║
║         Project Creator: Herman Swanepoel                 ║
╚═══════════════════════════════════════════════════════════╝
    """
    )

    # Check if git is installed
    try:
        subprocess.run(["git", "--version"], capture_output=True, check=True)
    except:
        print("❌ Git is not installed. Please install Git first.")
        sys.exit(1)

    # Get repository URL
    if len(sys.argv) > 1:
        repo_url = sys.argv[1]
    else:
        repo_url = input("Enter repository URL: ").strip()

    if not repo_url:
        print("❌ Repository URL is required")
        sys.exit(1)

    # Get target directory
    if len(sys.argv) > 2:
        target_dir = sys.argv[2]
    else:
        target_dir = input("Enter target directory (default: current directory): ").strip()
        if not target_dir:
            target_dir = "."

    # Run smart cloner
    cloner = SmartCloner(repo_url, target_dir)
    success = cloner.run()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
