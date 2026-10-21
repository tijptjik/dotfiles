import sys
import yaml  # Requires: pip install pyyaml

def get_genres(data, result):
    """Recursively extracts keys and string items from the nested structure."""
    if isinstance(data, dict):
        for key, value in data.items():
            if key: # Ensure key is not None
                result.add(str(key).strip())
            get_genres(value, result)
    elif isinstance(data, list):
        for item in data:
            get_genres(item, result)
    elif isinstance(data, str):
        result.add(data.strip())

def main():
    # Check if file path argument is provided
    if len(sys.argv) < 2:
        print("Usage: python script.py <path_to_yaml_file>")
        sys.exit(1)

    file_path = sys.argv[1]

    try:
        # Open with utf-8 to handle international characters in the source
        with open(file_path, 'r', encoding='utf-8') as f:
            tree = yaml.safe_load(f)

        all_genres = set()
        get_genres(tree, all_genres)

        # Sort alphabetically
        sorted_genres = sorted(list(all_genres))

        # Print each genre on a new line as plaintext
        for genre in sorted_genres:
            print(genre)

    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
