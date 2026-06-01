#!/bin/bash

# Ensure the script is run as root
if [[ $EUID -ne 0 ]]; then
    echo "This script must be run as root (use sudo)."
    exit 1
fi

# 1. Ask for number of users
read -p "How many users do you want to add? " count

# Array to keep usernames in memory
usernames=()

# 2. Collect usernames
for (( i=1; i<=count; i++ )); do
    read -p "Enter name for user $i: " name
    usernames+=("$name")
done

# 3. Ask for the public key
read -p "Paste your SSH public key here: " pubkey

# 4. Process each user
for user in "${usernames[@]}"; do
    echo "Creating user: $user..."
    
    # Create user with home directory and bash shell
    useradd -m -s /bin/bash "$user"
    
    # Set password to 1111
    echo "$user:1111" | chpasswd
    
    # Add to sudo group
    usermod -aG sudo "$user"
    
    # Set up SSH keys
    # We use 'su -' to run these commands as the user so permissions are correct
    su - "$user" -c "mkdir -p ~/.ssh && chmod 700 ~/.ssh && touch ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys && echo '$pubkey' >> ~/.ssh/authorized_keys"
    
    echo "User $user created successfully."
done

echo "All users have been added."
