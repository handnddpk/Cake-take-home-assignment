"""
Test script to verify SFTP paths and permissions
"""
import os
from airflow.providers.sftp.hooks.sftp import SFTPHook

# Test connection IDs
SOURCE_CONN_ID = 'sftp_source'
TARGET_CONN_ID = 'sftp_target'

def test_sftp_paths():
    print("Testing SFTP paths...")
    
    # Connect to source
    source_hook = SFTPHook(ssh_conn_id=SOURCE_CONN_ID)
    target_hook = SFTPHook(ssh_conn_id=TARGET_CONN_ID)
    
    source_client = source_hook.get_conn()
    target_client = target_hook.get_conn()
    
    # Check source home directory
    print("\n=== SOURCE SFTP ===")
    print(f"Current working directory: {source_client.getcwd()}")
    print(f"Home directory contents:")
    print(source_hook.list_directory('.'))
    print(f"Upload directory contents:")
    print(source_hook.list_directory('upload'))
    
    # Check target home directory
    print("\n=== TARGET SFTP ===")
    print(f"Current working directory: {target_client.getcwd()}")
    print(f"Home directory contents:")
    print(target_hook.list_directory('.'))
    print(f"Upload directory contents:")
    print(target_hook.list_directory('upload'))
    
    # Test creating a directory structure
    print("\n=== TESTING DIRECTORY CREATION ===")
    test_dir = 'upload/test_subdir/nested'
    test_file = 'upload/test_subdir/nested/test_file.txt'
    
    try:
        # Create nested directory
        parts = test_dir.split('/')
        current_path = ''
        for part in parts:
            if current_path:
                current_path = f"{current_path}/{part}"
            else:
                current_path = part
            
            try:
                target_client.stat(current_path)
                print(f"✓ Directory exists: {current_path}")
            except:
                target_client.mkdir(current_path)
                print(f"✓ Created directory: {current_path}")
        
        # Create test file
        with target_client.open(test_file, 'w') as f:
            f.write("Test content\n")
        print(f"✓ Created test file: {test_file}")
        
        # Verify file exists
        target_client.stat(test_file)
        print(f"✓ Verified file exists: {test_file}")
        
        # Clean up
        target_client.remove(test_file)
        print(f"✓ Cleaned up test file")
        
    except Exception as e:
        print(f"✗ Error during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_sftp_paths()
