"""Utils file"""

import os
import hashlib
import json

def read_hash_file(hash_file):
    """
    Read hash file.
    
    Arguments:
        - hash_file (str): Hash file path.

    Returns:
        - json.load (dict): Hashed dictionary.
    """
    try:
        with open(hash_file, 'r', encoding='utf-8') as pfile:
            return json.load(pfile)
    except (json.JSONDecodeError, FileExistsError, FileNotFoundError, PermissionError, Exception) as err:
        raise err

def write_hash_file(hash_file, hashes):
    """
    Write hash file.
    
    Creates a JSON file with hashes.
    
    Arguments:
        - hash_file (str): Hash file path.
        - hashes    (dict): Files hashes dictionary.
    """
    with open(hash_file, 'w', encoding='utf-8') as pfile:
        json.dump(hashes, pfile, indent=2)
 

def md5(file_path):
    """
    Create file md5 hash.
    
    Arguments:
        - file_path (str): File path.
    
    Returns:
        - md5 (hash): File's md5 hash.
    """
    with open(file_path, 'rb') as pfile:
        return hashlib.md5(pfile.read()).hexdigest()

def norm_file_path(files):
    """
    Nomralize file paths.
    
    Arguments:
        = files (list): List of files paths.
    
    Returns:
        - (list): List of normalized file paths.
    """
    return [os.path.normpath(file) for file in files]

def walk_directory(src_path, exclude, exclude_all, exclude_ext):
    """
    Walk directory recusively.

    Exclude all files, dirs and extensions needed.

    Arguments:
        - src_path    (str): Src path.
        - exclude     (list): List of files or directories to exclude.
        - exclude_all (list): List of files or directories to exclude in all subpaths.
        - exclude_ext (list): List of extensions to exclude in all subpaths.

    Returns:
        - process_files (list): List of files to process.
    """
    if exclude is not None:
        exclude[:] = norm_file_path(exclude)

    process_files = []

    for root, dirs, files in os.walk(src_path):
        if exclude is not None:
            # remove this paths
            dirs[:] = [d for d in dirs if os.path.normpath(os.path.join(root, d)) not in exclude]

        if exclude_all is not None:
            # remove paths globally
            dirs[:] = [d for d in dirs if d not in exclude_all]

        for file in files:
            file_path = os.path.normpath(os.path.join(root, file))
            _, ext = os.path.splitext(file_path)
            ext = ext.lstrip(".")

            # split it just to silence the linter
            exclude_flag = exclude is not None and file_path in exclude
            exclude_all_flag = exclude_all is not None and file in exclude_all
            exclude_ext_flag = exclude_ext is not None and ext in exclude_ext

            if exclude_flag or exclude_all_flag or exclude_ext_flag:
                continue
            process_files.append(file_path)

    return norm_file_path(process_files)
