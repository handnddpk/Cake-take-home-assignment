"""
Test script to verify the sync_files logic
This simulates what the DAG will do
"""
import os
from airflow.providers.sftp.hooks.sftp import SFTPHook

SOURCE_CONN_ID = 'sftp_source'
TARGET_CONN_ID = 'sftp_target'
SYNC_ROOT_DIR = '/upload'

def test_sync_logic():
    print("Testing sync logic...")
    
    source_hook = SFTPHook(ssh_conn_id=SOURCE_CONN_ID)
    target_hook = SFTPHook(ssh_conn_id=TARGET_CONN_ID)
    
    # Simulate discovered files (what discover_source_files returns)
    # These would come from list_files_recursive
    test_files = [
        {
            'path': '/upload/backups/config_backup.txt',
            'relative_path': 'backups/config_backup.txt',
            'size': 100
        },
        {
            'path': '/upload/reports/2024/Q1/sales_q1.csv',
            'relative_path': 'reports/2024/Q1/sales_q1.csv',
            'size': 200
        }
    ]
    
    print(f"\nSYNC_ROOT_DIR: '{SYNC_ROOT_DIR}'")
    print(f"Number of test files: {len(test_files)}\n")
    
    for file_info in test_files:
        source_path = file_info['path']
        relative_path = file_info['relative_path']
        
        print(f"{'='*60}")
        print(f"Processing file:")
        print(f"  Source path: {source_path}")
        print(f"  Relative path: {relative_path}")
        
        # This is the exact logic from sync_files function
        target_path = os.path.join(SYNC_ROOT_DIR.lstrip('/'), relative_path).replace('\\', '/')
        
        print(f"  Target path: {target_path}")
        
        # Verify the target path is correct
        expected_target = f"upload/{relative_path}"
        if target_path == expected_target:
            print(f"  ✓ Target path is CORRECT")
        else:
            print(f"  ✗ Target path is WRONG! Expected: {expected_target}")
        
        # Test directory creation
        dir_path = os.path.dirname(target_path)
        print(f"  Target directory: {dir_path}")
        
        try:
            # Create directory structure
            parts = dir_path.strip('/').split('/')
            current_path = ''
            target_client = target_hook.get_conn()
            
            for part in parts:
                if not part:
                    continue
                    
                if current_path:
                    current_path = f"{current_path}/{part}"
                else:
                    current_path = part
                    
                try:
                    target_client.stat(current_path)
                    print(f"    ✓ Directory exists: {current_path}")
                except:
                    target_client.mkdir(current_path)
                    print(f"    ✓ Created directory: {current_path}")
            
            # Create a test file
            test_content = f"Test content for {os.path.basename(target_path)}"
            with target_client.open(target_path, 'w') as f:
                f.write(test_content)
            print(f"  ✓ Successfully created file: {target_path}")
            
            # Verify file exists
            stat_info = target_client.stat(target_path)
            print(f"  ✓ File verified, size: {stat_info.st_size} bytes")
            
        except Exception as e:
            print(f"  ✗ ERROR: {e}")
            import traceback
            traceback.print_exc()
    
    # Show final directory structure
    print(f"\n{'='*60}")
    print("Final target directory structure:")
    print(f"\nTarget upload directory contents:")
    try:
        target_client = target_hook.get_conn()
        
        def list_recursive(path, indent=0):
            try:
                items = target_hook.list_directory(path)
                for item in sorted(items):
                    item_path = f"{path}/{item}".replace('//', '/')
                    try:
                        stat_info = target_client.stat(item_path)
                        import stat as stat_module
                        if stat_module.S_ISDIR(stat_info.st_mode):
                            print(f"{'  ' * indent}📁 {item}/")
                            list_recursive(item_path, indent + 1)
                        else:
                            print(f"{'  ' * indent}📄 {item} ({stat_info.st_size} bytes)")
                    except:
                        pass
            except:
                pass
        
        list_recursive('upload')
    except Exception as e:
        print(f"Error listing directory: {e}")

if __name__ == '__main__':
    test_sync_logic()
