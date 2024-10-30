import argparse
import os
import re
import socket
import subprocess
import sys

from lib.conf import *
from lib.lang import language_options, default_language_code

script_mode = NATIVE

def check_python_version():
    current_version = sys.version_info[:2]  # (major, minor)
    if current_version < min_python_version or current_version > max_python_version:
        error = f"""********** Error: Your OS Python version is not compatible! (current: {current_version[0]}.{current_version[1]})
        Please create a virtual python environment verrsion {min_python_version[0]}.{min_python_version[1]} or {max_python_version[0]}.{max_python_version[1]} 
        with conda or python -v venv **********"""
        print(error)
        return False
    else:
        return True
        
def check_and_install_requirements(file_path):
    if not os.path.exists(file_path):
        print(f"Warning: File {file_path} not found. Skipping package check.")
    try:
        from importlib.metadata import version, PackageNotFoundError
        with open(file_path, 'r') as f:
            contents = f.read().replace('\r', '\n')
            packages = [pkg.strip() for pkg in contents.splitlines() if pkg.strip()]

        missing_packages = []
        for package in packages:
            # Extract package name without version specifier
            pkg_name = re.split(r'[<>=]', package)[0].strip()
            try:
                installed_version = version(pkg_name)
            except PackageNotFoundError:
                print(f"{package} is missing.")
                missing_packages.append(package)

        if missing_packages:
            print("\nInstalling missing packages...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"] + missing_packages)
            except subprocess.CalledProcessError as e:
                print(f"Failed to install packages: {e}")
                return False

    except Exception as e:
        print(f"An error occurred: {e}")
        
    return True

def check_dictionary(language):
    import unidic
    import spacy.cli
    
    version_obj = sys.version_info
    version = f"{version_obj.major}.{version_obj.minor}"

    required_model = f"{language}_core_web_sm"

    if not os.path.isdir(unidic.DICDIR):
        if not os.listdir(unidic.DICDIR):
            try:
                print("*** No default dictionary found! Trying to download it... ***")
                subprocess.run([sys.executable, "-m", "unidic", "download"], check=True)
                print("Successfully downloaded UniDic.")
                return True
            except subprocess.CalledProcessError as e:
                print(f"Failed to download UniDic: {e}")
                return False
            except Exception as e:
                print(f"Error during UniDic download: {e}")
                return False
        fi

    # Check if the required model is already installed in spaCy
    info = spacy.cli.info()
    installed_models = info.get("pipelines", {}).keys()
    if required_model in installed_models:
        return True

    try:
        print("*** Default spaCy model is missing! Trying to download it... ***")
        subprocess.run([sys.executable, "-m", "spacy", "download", required_model], check=True)
        print("Successfully downloaded spaCy model.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Failed to download spaCy model: {e}")
        return False
    except Exception as e:
        print(f"Error during spaCy model download: {e}")
        return False

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('0.0.0.0', port)) == 0

def main():
    global script_mode, ebooks_dir
    print("*********************************",os.environ.get("TTS_CACHE"))
    
    # Convert the list of languages to a string to display in the help text
    language_options_str = ", ".join(language_options)

    # Argument parser to handle optional parameters with descriptions
    parser = argparse.ArgumentParser(
        description="Convert eBooks to Audiobooks using a Text-to-Speech model. You can either launch the Gradio interface or run the script in headless mode for direct conversion.",
        epilog="""\
Example usage:    
Windows:
    headless:
    ebook2audiobook.cmd --headless --ebook 'path_to_ebook' --voice 'path_to_voice' --language en --use_custom_model --custom_model 'model.zip' --custom_config config.json --custom_vocab vocab.json
    Graphic Interface:
    ebook2audiobook.cmd
Linux/Mac:
    headless:
    ./ebook2audiobook.sh --headless --ebook 'path_to_ebook' --voice 'path_to_voice' --language en --use_custom_model --custom_model 'model.zip' --custom_config config.json --custom_vocab vocab.json
    Graphic Interface:
    ./ebook2audiobook.sh
""",
        formatter_class=argparse.RawTextHelpFormatter
    )
    options = [
        "--script_mode", "--share", "--headless", "--ebook", "--ebooks_dir",
        "--voice", "--language", "--device", "--use_custom_model", "--custom_model", 
        "--custom_config", "--custom_vocab", "--custom_model_url", "--temperature",
        "--length_penalty", "--repetition_penalty", "--top_k", "--top_p", "--speed",
        "--enable_text_splitting", "--version"
    ]
    parser.add_argument(options[0], type=str,
                        help="Force the script to run in 'native' or 'docker_utils'")
    parser.add_argument(options[1], action="store_true",
                        help="Enable a public shareable Gradio link. Defaults to False.")
    parser.add_argument(options[2], nargs='?', const=True, default=False,
                        help="Run in headless mode. Defaults to True if the flag is present without a value, False otherwise.")
    parser.add_argument(options[3], type=str,
                        help="Path to the ebook file for conversion. Required in headless mode.")
    parser.add_argument(options[4], nargs='?', const="default", type=str,
                        help=f"Path to the directory containing ebooks for batch conversion. Defaults to '{os.path.basename(ebooks_dir)}' if 'default' value is provided.")
    parser.add_argument(options[5], type=str,
                        help="Path to the target voice file for TTS. Optional, uses a default voice if not provided.")
    parser.add_argument(options[6], type=str, default="en",
                        help=f"Language for the audiobook conversion. Options: {language_options_str}. Defaults to English (en).")
    parser.add_argument(options[7], type=str, default="cpu", choices=["cpu", "gpu"],
                        help=f"Type of processor unit for the audiobook conversion. If not specified: check first if gpu available, if not cpu is selected.")
    parser.add_argument(options[8], action="store_true",
                        help="Use a custom TTS model. Defaults to False. Must be True to use custom models.")
    parser.add_argument(options[9], type=str,
                        help="Path to the custom model file (.pth). Required if using a custom model.")
    parser.add_argument(options[10], type=str,
                        help="Path to the custom config file (config.json). Required if using a custom model.")
    parser.add_argument(options[11], type=str,
                        help="Path to the custom vocab file (vocab.json). Required if using a custom model.")
    parser.add_argument(options[12], type=str,
                        help=("URL to download the custom model as a zip file. Optional, but will be used if provided. "
                              "Examples include David Attenborough's model: "
                              "'https://huggingface.co/drewThomasson/xtts_David_Attenborough_fine_tune/resolve/main/Finished_model_files.zip?download=true'. "
                              "More XTTS fine-tunes can be found on my Hugging Face at 'https://huggingface.co/drewThomasson'."))
    parser.add_argument(options[13], type=float, default=0.65,
                        help="Temperature for the model. Defaults to 0.65. Higher temperatures lead to more creative outputs.")
    parser.add_argument(options[14], type=float, default=1.0,
                        help="A length penalty applied to the autoregressive decoder. Defaults to 1.0. Not applied to custom models.")
    parser.add_argument(options[15], type=float, default=2.0,
                        help="A penalty that prevents the autoregressive decoder from repeating itself. Defaults to 2.0.")
    parser.add_argument(options[16], type=int, default=50,
                        help="Top-k sampling. Lower values mean more likely outputs and increased audio generation speed. Defaults to 50.")
    parser.add_argument(options[17], type=float, default=0.8,
                        help="Top-p sampling. Lower values mean more likely outputs and increased audio generation speed. Defaults to 0.8.")
    parser.add_argument(options[18], type=float, default=1.0,
                        help="Speed factor for the speech generation. Defaults to 1.0.")
    parser.add_argument(options[19], action="store_true",
                        help="Enable splitting text into sentences. Defaults to False.")
    parser.add_argument(options[20], action="version",version=f"ebook2audiobook version {version}",
                        help="Show the version of the script and exit")

    for arg in sys.argv:
        if arg.startswith("--") and arg not in options:
            print(f"Error: Unrecognized option '{arg}'")
            sys.exit(1)
            
    args = parser.parse_args()

    # Check if the port is already in use to prevent multiple launches
    if not args.headless and is_port_in_use(web_interface_port):
        print(f"Error: Port {web_interface_port} is already in use. The web interface may already be running.")
        sys.exit(1)
    
    script_mode = args.script_mode if args.script_mode else script_mode
    
    if script_mode == NATIVE:
        check_pkg = check_and_install_requirements(requirements_file)
        if check_pkg:
            check_dic = check_dictionary(args.language)
            if not check_dic:
                sys.exit(1)
        else:
            sys.exit(1)
    
    from lib.functions import web_interface, convert_ebook

    # Conditions based on the --headless flag
    if args.headless:
        # Condition to stop if both --ebook and --ebooks_dir are provided
        if args.ebook and args.ebooks_dir:
            print("Error: You cannot specify both --ebook and --ebooks_dir in headless mode.")
            sys.exit(1)

        # Condition 1: If --ebooks_dir exists, check value and set 'ebooks_dir'
        if args.ebooks_dir:
            if args.ebooks_dir == "default":
                print(f"Using the default ebooks_dir: {ebooks_dir}")
                ebooks_dir =  os.path.abspath(ebooks_dir)
            else:
                # Check if the directory exists
                if os.path.exists(args.ebooks_dir):
                    ebooks_dir = os.path.abspath(args.ebooks_dir)
                else:
                    print(f"Error: The provided --ebooks_dir '{args.ebooks_dir}' does not exist.")
                    sys.exit(1)
                    
            if os.path.exists(ebooks_dir):
                for file in os.listdir(ebooks_dir):
                    # Process files with supported ebook formats
                    if any(file.endswith(ext) for ext in supported_ebook_formats):
                        full_path = os.path.join(ebooks_dir, file)
                        print(f"Processing eBook file: {full_path}")
                        args.ebook = full_path
                        convert_ebook(args, False)
            else:
                print(f"Error: The directory {ebooks_dir} does not exist.")
                sys.exit(1)
        elif args.ebook:
            convert_ebook(args, False)
        else:
            print("Error: In headless mode, you must specify either an ebook file using --ebook or an ebook directory using --ebooks_dir.")
            sys.exit(1)       
    else:
        passed_arguments = sys.argv[1:]
        allowed_arguments = {'--share', '--script_mode'}
        passed_args_set = {arg for arg in passed_arguments if arg.startswith('--')}
        if passed_args_set.issubset(allowed_arguments):
             web_interface(args.script_mode, args.share, True)
        else:
            print("Error: In non-headless mode, no option or only '--share' can be passed")
            sys.exit(1)

if __name__ == '__main__':
    if not check_python_version():
        sys.exit(1)
    else:
        main()
