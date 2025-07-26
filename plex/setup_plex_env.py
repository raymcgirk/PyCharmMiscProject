import platform
import subprocess

def set_env_var(var, value):
    system = platform.system()

    if system == "Windows":
        # Persist the environment variable using setx
        subprocess.run(["setx", var, value], shell=True)
        print(f"✅ Set {var} in user environment.")
    else:
        # Fallback: Write to .env file (or you can customize this for your shell)
        with open(".env", "a") as f:
            f.write(f"{var}={value}\n")
        print(f"✅ Appended {var} to .env file (non-Windows fallback).")

def main():
    print("🔧 Plex Environment Variable Setup")
    print("You can use this to register one or more Plex servers.")
    print()

    while True:
        server_key = input("Enter a short name for this server (e.g., main, backup): ").strip()
        if not server_key:
            print("❌ Server key is required.")
            continue

        token = input("Enter the Plex token for this server: ").strip()
        base_url = input("Enter the base URL (e.g., http://192.168.1.10:32400): ").strip()

        if not token or not base_url:
            print("❌ Both token and base URL are required.")
            continue

        # Construct env var names
        token_var = f"PLEX_TOKEN_{server_key}"
        url_var = f"PLEX_BASE_URL_{server_key}"

        # Set them
        set_env_var(token_var, token)
        set_env_var(url_var, base_url)

        another = input("Add another server? (y/n): ").strip().lower()
        if another != "y":
            break

    print("\n✅ Done. You may need to restart your terminal or IDE for changes to take effect.")

if __name__ == "__main__":
    main()
