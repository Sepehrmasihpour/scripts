#!/bin/bash

# Ensure the script is run as root
if [[ $EUID -ne 0 ]]; then
    echo "This script must be run as root (use sudo)."
    exit 1
fi

# 1. Ask for number of users
read -p "How many users do you want to add? " count

# Validate count is an integer
if ! [[ "$count" =~ ^[0-9]+$ ]] || [[ "$count" -lt 1 ]]; then
    echo "Error: Please enter a valid positive number."
    exit 1
fi

# Array to keep usernames in memory
usernames=()

# 2. Collect usernames
for (( i=1; i<=count; i++ )); do
    read -p "Enter name for user $i: " name
    
    # Basic username validation
    if ! [[ "$name" =~ ^[a-z_][a-z0-9_-]*[$]?$ ]]; then
        echo "Error: Invalid username: $name"
        echo "Use lowercase letters, numbers, underscores, or hyphens. Username should start with a letter or underscore."
        exit 1
    fi
    
    usernames+=("$name")
done

# 3. Ask for the public key that will be allowed to log in as these users
read -p "Paste your SSH public key for login here: " pubkey

# Basic public key validation
if [[ -z "$pubkey" ]]; then
    echo "Error: Public key cannot be empty."
    exit 1
fi

# 4. Process each user
for user in "${usernames[@]}"; do
    echo "----------------------------------------"
    echo "Processing user: $user"
    
    # Check if user already exists
    if id "$user" &>/dev/null; then
        echo "User $user already exists. Skipping user creation."
    else
        echo "Creating user: $user..."
        
        # Create user with home directory and bash shell
        useradd -m -s /bin/bash "$user"
        
        # Set password to 1111
        echo "$user:1111" | chpasswd
        
        # Add to sudo group
        usermod -aG sudo "$user"
        
        echo "User $user created."
    fi
    
    # Set up SSH directory and authorized_keys for inbound SSH login
    echo "Setting up authorized_keys for $user..."
    
    install -d -m 700 -o "$user" -g "$user" "/home/$user/.ssh"
    
    touch "/home/$user/.ssh/authorized_keys"
    chmod 600 "/home/$user/.ssh/authorized_keys"
    chown "$user:$user" "/home/$user/.ssh/authorized_keys"
    
    # Add public key if it is not already there
    if grep -qxF "$pubkey" "/home/$user/.ssh/authorized_keys"; then
        echo "Public login key already exists in /home/$user/.ssh/authorized_keys"
    else
        echo "$pubkey" >> "/home/$user/.ssh/authorized_keys"
        echo "Public login key added to /home/$user/.ssh/authorized_keys"
    fi
    
    # Create an outbound SSH key pair for this user, if it does not already exist
    echo "Creating SSH key pair for $user..."
    
    if [[ -f "/home/$user/.ssh/id_ed25519" ]]; then
        echo "SSH key pair already exists for $user. Skipping key generation."
    else
        sudo -u "$user" ssh-keygen -t ed25519 \
        -f "/home/$user/.ssh/id_ed25519" \
        -C "$user@$(hostname)" \
        -N ""
        
        echo "SSH key pair created for $user."
    fi
    
    # Make sure ownership and permissions are correct
    chown -R "$user:$user" "/home/$user/.ssh"
    chmod 700 "/home/$user/.ssh"
    chmod 600 "/home/$user/.ssh/authorized_keys"
    
    if [[ -f "/home/$user/.ssh/id_ed25519" ]]; then
        chmod 600 "/home/$user/.ssh/id_ed25519"
    fi
    
    if [[ -f "/home/$user/.ssh/id_ed25519.pub" ]]; then
        chmod 644 "/home/$user/.ssh/id_ed25519.pub"
    fi
    
    echo "User $user setup completed."
done

echo "----------------------------------------"
echo "All users have been processed."
echo
echo "Generated public keys:"
echo

for user in "${usernames[@]}"; do
    if [[ -f "/home/$user/.ssh/id_ed25519.pub" ]]; then
        echo "Public key for $user:"
        cat "/home/$user/.ssh/id_ed25519.pub"
        echo
    fi
done
