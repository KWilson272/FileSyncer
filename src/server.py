"""Module to function as the host server for the file syncer system."""

import os
import sys
from concurrent import futures

import yaml
import grpc

import syncer_pb2
import syncer_pb2_grpc

BUFFER_SIZE = 1024 * 1024 # 1 Megabyte

class FileSyncerServicer(syncer_pb2_grpc.FileServerServicer):
    """Implementation of the FileServerServicer to handle communicating
    information from the host machine to the client.

    Fields:
        paths_by_keys (dictionary<string, string>) - 
            Maps the file keys the client will use to make requests to file paths
    """

    def __init__(self, paths_by_key):
        """The constructor for the FileSyncerServicer class

        Parameters:
            paths_by_keys (dictionary<string, string>) - 
                a dictionary of string file paths mapped to string file keys
        """
        self.paths_by_key = paths_by_key

    def req_file_desc(self, request, context):
        """Receives a file key from the client and returns a description
        containing the following:
            1. A code to communicate if the file can be downloaded
            2. The requested file's name
            3. The requested file's last modification time
            4. The request file's size
        
        In the case that the file is for some reason not downloadable,
        the returned file description object's fields will be default
        outside of the FileState code.

        Parameters:
            request (FileKey) - Contains the file key id the client requested
            context (RPC Context) - The RPC call context

        Returns:
          The above information in a FileDesc object
        """

        file_key  = request.id
        file_path = self.paths_by_key[file_key]
        file_desc = syncer_pb2.FileDesc()

        # If this hosting server does not have any key registered with the provided ID
        if file_key not in self.paths_by_key:
            file_desc.state = syncer_pb2.UNKNOWN_FILE_KEY

        elif not os.path.isfile(file_path):
            file_desc.state = syncer_pb2.FILE_NOT_PRESENT

        elif not os.access(file_path, os.R_OK):
            file_desc.state = syncer_pb2.FILE_NOT_READABLE

        else:  
            file_desc.state = syncer_pb2.DOWNLOAD_POSSIBLE
            file_desc.file_name = os.path.basename(file_path)
            file_desc.file_size = os.path.getsize(file_path)

            # Modification time can be older than creation time on some machines
            mod_time = os.path.getmtime(file_path)
            make_time = os.path.getctime(file_path)
            most_recent_time = mod_time if mod_time > make_time else make_time
            file_desc.last_modification_time = most_recent_time

        return file_desc
    
    # Provides the provided file to the client over a stream 
    def download(self, request, context):
        """Streams the provided file over the network via a unary stream

        Parameters:
            request (FileKey) - Contains the file key id the client requested
            context (RPC Context) - The RPC call context
       
        Yields:
            a FileChunk containing parts of the file
        """
        # will not be called by client unless the file was confirmed present
        file_path = self.paths_by_key[request.id]

        try:
            with open(file_path, 'rb') as file:
                chunk = syncer_pb2.FileChunk()
                while True:
                    chunk.content = file.read(1024 * 1024) # 1 megabyte chunk size
                    if not chunk.content:
                        break

                    chunk_counter += 1
                    yield chunk

        except OSError as e:
            print('Encountered an error while trying to read a file')
            print(e.strerror)
        return

def init_service():
    try:
        yml_path = os.path.join(os.getcwd(), 'config', 'server.yml')
        with open(yml_path, 'r') as file:
            options = yaml.safe_load(file)

            host_address = options['Address']
            host_port = options['Port']
            address = host_address +':' + host_port
            
            paths_by_key = options['Files']
            syncer_service = FileSyncerServicer(paths_by_key)

            server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
            syncer_pb2_grpc.add_FileServerServicer_to_server(syncer_service, server)
            server.add_insecure_port(address)

            server.start()
            server.wait_for_termination()

    except OSError as e:
        print('Could not load the server.yml')
        print(e.strerror)
        sys.exit()

if __name__ == '__main__':
    init_service()