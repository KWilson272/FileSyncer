import os
import sys
import shutil
import time
from datetime import date

import yaml
import grpc

import syncer_pb2
import syncer_pb2_grpc

class BackupHandler:
    """Handles creating new backups and their necessary directories, as well as
    deleting backups when the amount of stored files grows too large.

    Fields:
        _dir_path (Path) - The path to the Backups directory
        _max_backups (int) - The maximum amount of backed up files a given 
                            file ID can have
    """

    def __init__(self):
        """The constructor of the BackupHandler Class."""
        self._dir_path = os.path.join(os.getcwd(), 'Backups')
        self._max_backups = 5

    def clean_dir(self, file_id):
        """Removes excess files from the backup directory for the provided
          file id. Excess is determined by the _max_backups variable, and 
          files are removed on the basis of oldest creation time first.

        Parameters:
            file_id (String) - the ID passed to the host server when 
                            requesting a file to download
        """
        backup_dir = os.path.join(self._dir_path, file_id, '')
        if not os.path.exists(backup_dir):
            return
 
        old_backups = os.listdir(backup_dir)
        if len(old_backups) < self._max_backups:
            return
        
        paths = []
        for file in old_backups:
            file_path = os.path.join(backup_dir, file)
            paths.append(file_path)

        # Get the oldest backup and remove it
        paths.sort(key=lambda f: os.path.getctime(f))
        os.remove(paths[0])
        print(f'Removed an old backup from {backup_dir}.')
        return

    def back_up(self, file_id, old_file):
        """Copies the provided file into its specified backup folder.
        
        Parameters:
            file_id (String) - the file ID used to retrieve the downloaded 
                            file from the host
            old_file (Path) - the path to the out-of-date file that is to be
                            backed up
        """
        print(f'Backing up {old_file}.')
        backup_dir = os.path.join(self._dir_path, file_id)
        try:
            os.makedirs(backup_dir)
        except FileExistsError:
            pass 

        # Append the date for user reference
        date_str = str(date.today())
        base_path = os.path.join(backup_dir, file_id + '_' + date_str) 
        file_extension = os.path.splitext(old_file)[1]

        # If this program is run multiple times a day, there is a 
        # possibility for multiple backups to be made. To prevent
        # conflicting file names, we will use a numbering system
        dupe_counter = 0
        backup_file = base_path + file_extension
        while os.path.exists(backup_file):
            dupe_counter += 1
            backup_file = base_path + '_' + str(dupe_counter) + file_extension

        shutil.copy(old_file, backup_file)
        os.remove(old_file)
    

def display_file_state(file_desc, file_key):
    """Helper function to display the error state returned by the host machine
        
    Parameters:
        file_desc (FileDesc) - the File description returned by the host 
                            machine; contains the error state
        file_key (FileKey) - the FileKey used in the failed resource 
                            request to the host
    """
    file_state = file_desc.state
    if file_state == syncer_pb2.UNKNOWN_FILE_KEY:
        print('The provided key could not be found on the host machine. What was read:', file_key.id)
    elif file_state == syncer_pb2.FILE_NOT_PRESENT:
        print('The host machine could not find any file mapped to the provided key.')
    elif file_state == syncer_pb2.FILE_NOT_READABLE:
        print('The host machine is unable to read the file over the network.')


def find_old_file(install_dir, replace_name, targ_extension):
    """Returns the path to the file that is being replaced by the updated one 
    received from the host.
    
    Parameters:
        install_dir (Path) - the Path to the directory the updated file will
                            be installed in
        replace_name (String) - The rough name of the old file being searched
                            for. This can exclude version numbers, but the 
                            provided name MUST be included in the returned 
                            file's name
        targ_extension (String) - The file extension of the target file
    """
    for file in os.listdir(install_dir):  
        path = os.path.join(install_dir, file)
        extension = os.path.splitext(file)[1]
        if os.path.isdir(path) or extension != targ_extension:
            continue
        if replace_name in file:
            return path
    return None

def main():
    print('FileSyncer client Started!')
    
    yml_path = os.path.join(os.getcwd(), 'config', 'client.yml')
    with open(yml_path, 'r') as file:
        options = yaml.safe_load(file)
    
    if options == None:
        print('Unable to load options from the client.yml. The program can not continue')
        sys.exit(0)

    backup_handler = BackupHandler()

    host_address = options['Address']
    host_port = options['Port']
    address = host_address + ':' + host_port
    files = options['Files']

    with grpc.insecure_channel(address) as channel:
        stub = syncer_pb2_grpc.FileServerStub(channel)

        for key_id in files:
            file_key = syncer_pb2.FileKey()
            file_key.id = key_id

            file_desc = stub.req_file_desc(file_key)
            if not file_desc.state == syncer_pb2.DOWNLOAD_POSSIBLE:
                display_file_state(file_desc, file_key)
                continue
            
            download_info = files[key_id]
            install_path = download_info['Path']
            replace_name = download_info['Replace']

            file_extension = os.path.splitext(file_desc.file_name)[1]
            active_file = find_old_file(install_path, replace_name, file_extension)

            if active_file != None:
                creation_time = os.path.getctime(active_file)
                mod_time = os.path.getmtime(active_file)
                most_recent_time = mod_time if mod_time > creation_time else creation_time
                if most_recent_time > file_desc.last_modification_time:
                    continue
            
            start_time = time.time_ns()

            new_name = file_desc.file_name + ".Temp"
            new_path = os.path.join(install_path, new_name)
            print(f"Downloading {file_desc.file_name} as {new_name}")
            with open(new_path, 'wb') as file:
                for chunk in stub.download(file_key):
                    file.write(chunk.content)

            if not os.path.getsize(new_path) == file_desc.file_size:
                byte_diff = os.path.getsize(new_path) - file_desc.file_size
                print(f"Download failed, difference: {byte_diff} bytes")
                continue

            print("Download successful!")
            time_delta = time.time_ns() - start_time
            time_delta /= 1e+9 # Convert from ns -> seconds
            string_delta = '{0:.3f}'.format(time_delta)
            print(f"Finished downloading the file, took: {string_delta} seconds")

            if active_file != None:
                backup_handler.clean_dir(file_key.id)
                backup_handler.back_up(file_key.id, active_file)
            
            final_path = os.path.join(install_path, file_desc.file_name)
            os.rename(new_path, final_path)

if __name__ == '__main__':
    main()
