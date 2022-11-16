import argparse
import logging
import os
import git.exc
import requests
import shutil
from tqdm import tqdm
from git import Repo

# from configuration.repository import supported_languages, supported_sort_by
supported_languages = ["python"]
supported_sort_by = ["stars"]
# from helpers.language import extension_mappings
extension_mappings = {"python": "py"}

from pathlib import Path
from langdetect import detect

# MIN_LINES_PER_FILE = 50
MIN_LINES_PER_FILE = 200
# MAX_LINES_PER_FILE = 1000
MAX_LINES_PER_FILE = 1000000


class RepositoryCloner:
    def __init__(self, language="python", sort_by="stars", n_results=100):
        if language not in supported_languages:
            logger.info(f"{language} is still not supported language by the logsight.ai autologger")
        if sort_by not in supported_sort_by:
            logger.info(f"{language} is still not supported sorting method by the logsight.ai autologger")
        self.language = language
        self.sort_by = sort_by
        self.n_results = n_results
        self.request_link = f"https://api.github.com/search/repositories?q=" \
                            f"language:{self.language}" \
                            f"&sort={self.sort_by}" \
                            f"&order=desc" \
                            f"&per_page={n_results}"

    def clone_repositories(self, output_dir="../data/repositories/"):
        if not os.path.isdir(output_dir):
            os.makedirs(output_dir)
            logger.info(f'Created folder: {output_dir} successfully')
        repositories = requests.get(self.request_link).json()["items"]
        for repository in tqdm(repositories):
            if repository["description"] and detect(repository["description"]) == "en":
                logger.info(f'Cloning repository : {repository["html_url"]}')
                try:
                    Repo.clone_from(repository["html_url"], output_dir + f"{self.language}/" + repository["name"])
                except git.exc.GitCommandError as e:
                    logger.error(e)
        return repositories

    def filter_repository_files(self, repository_dir='../data/repositories/', output_dir='../data/filter/'):
        if not os.path.isdir(output_dir):
            os.makedirs(output_dir)
            logger.debug(f'Created folder: {output_dir} successfully')
        file_handler = logging.FileHandler(f"{output_dir}filtering.log")
        file_handler.setLevel(logging.INFO)
        logger.addHandler(file_handler)
        logger.debug(f"Filtering files that contain the {self.language} language extension")
        repos = list(Path(f"{repository_dir}{self.language}").glob(f"*{os.sep}"))
        repo_count = len(repos)
        # logger.debug(list(map(str, repos[:10]))); exit()
        continuous_index = 1
        skipped_repos_count = 0
        included_repos = []
        for repo_num, repo in enumerate(repos):
            repo_is_included = False
            files = list(repo.rglob(f"*.{extension_mappings[self.language]}"))
            # cmd = f'find {str(repo)}/ -type f -iname "*.py" | xargs grep -l -e "^import logging" | wc -l'
            # xargs -I arg is A LOT slower but handles spaces in file names. Grep used instead of rg for compatability
            # cmd = f'find {str(repo)}/ -type f -iname "*.py" | xargs -I'+' {} grep -l -e "^import logging" {} | wc -l'
            # find -print0 and xargs -0 use the ASCII NUL character as a separator which helps with spaces in filenames
            # cmd = f'find {str(repo)}/ -type f -iname "*.py" -print0 | xargs -0 -I'+' {} grep -l -e "^import logging" {} | wc -l'
            # Now works without xargs -I {}:
            cmd = f'find {str(repo)}/ -type f -iname "*.py" -print0 | xargs -0 grep -l -e "^import logging" | wc -l'
            stream = os.popen(cmd)
            files_importing_logging_count = int(stream.read())
            if files_importing_logging_count == 0:
                logger.debug(f"{repo_num + 1}/{repo_count} "
                             f"Skipping {str(repo.name)} because it doesn't use logging at all.")
                skipped_repos_count += 1
                continue
            for index, file in enumerate(files):
                if not file.is_file(): continue
                # with open(file, 'r', errors='replace') as f:
                try:
                    with open(file, 'r') as f:
                        f_s = f.readlines()
                except UnicodeDecodeError as e:
                    logger.debug(f"{type(e)} encountered while processing {str(file)}")
                    continue
                if MIN_LINES_PER_FILE <= len(f_s) < MAX_LINES_PER_FILE:
                    # shutil.copy2(file, output_dir + str(index) + f".{extension_mappings[self.language]}")
                    shutil.copy2(file, output_dir + str(continuous_index) + f".{extension_mappings[self.language]}")
                    continuous_index += 1
                    repo_is_included = True
            if repo_is_included:
                included_repos.append(str(repo.name))
        logger.debug("Filtering finished successfully.")
        logger.info(f"Skipped {skipped_repos_count} out of {repo_count} repositories due to lack of logging.\n"
                    f"Included {continuous_index} {self.language} files "
                    f"from {repo_count - skipped_repos_count} repositories:")
        logger.info(str(included_repos))


if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("-min", "--minimum", type=int,
                            help="Minimum required number of lines to include a source code file in the filtering.")
    arg_parser.add_argument("-max", "--maximum", type=int,
                            help="Maximum allowed number of lines to include a source code file in the filtering.")
    args = arg_parser.parse_args()
    if args.minimum: MIN_LINES_PER_FILE = args.minimum
    if args.maximum: MAX_LINES_PER_FILE = args.maximum

    logger = logging.getLogger(__name__)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    logger.addHandler(console_handler)
    logger.setLevel(logging.DEBUG)

    repo_dir = "../repos/python/300repos/"
    filter_dir = f"../repos/python/filter/300repos_minus_nonlogged_min{MIN_LINES_PER_FILE}_max{MAX_LINES_PER_FILE}/"

    # repo_dir = "/Users/nickkeutel/code/ma/100repos/"
    # filter_dir = f"/Users/nickkeutel/code/ma/filter/100repos_minus_nonlogged_min{MIN_LINES_PER_FILE}_max{MAX_LINES_PER_FILE}/"

    repository_cleaner = RepositoryCloner(n_results=100)
#     repository_cleaner.clone_repositories(output_dir=repo_dir)
    repository_cleaner.filter_repository_files(repository_dir=repo_dir, output_dir=filter_dir)
