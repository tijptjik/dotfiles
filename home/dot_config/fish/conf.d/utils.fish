# ~/.config/fish/conf.d/utils.fish
# #######################
# FISH : UTILS
# #######################

# Author : Mart van de Ven
# Contact : https://type.hk

################################
###  PROMPT
################################

# Customize fish greeting message
function fish_greeting
  fortune | xargs -0 docker run --rm mpepping/ponysay:latest
end

#################################
### FILE & ARCHIVE MANAGEMENT
#################################

function mkd -d "Create a new directory and enter it"
  mkdir -p $argv; and cd $argv
end


function extract --description "Expand or extract bundled & compressed files"
  set --local ext (echo $argv[1] | awk -F. '{print $NF}')
  switch $ext
    case tar  # non-compressed, just bundled
      tar -xvf $argv[1]
    case gz
      if test (echo $argv[1] | awk -F. '{print $(NF-1)}') = tar  # tar bundle compressed with gzip
        tar -zxvf $argv[1]
      else  # single gzip
        gunzip $argv[1]
      end
    case zst
      if test (echo $argv[1] | awk -F. '{print $(NF-1)}') = tar  # tar bundle compressed with zst
        tar --zstd -xvf $argv[1]
      else  # single zst
        unzstd $argv[1]
      end
    case tgz  # same as tar.gz
      tar -zxvf $argv[1]
    case bz2  # tar compressed with bzip2
      tar -jxvf $argv[1]
    case rar
      unrar x $argv[1]
    case zip
      unzip $argv[1]
    case '*'
      echo "unknown extension"
  end
end

alias arc=extract

function mktar -d "Create a tar archive from a file or directory"
  tar cvf  $argv.tar $argv;
end

function mktgz -d "Create a tar gz archive from a file or directory"
  tar cvzf  $argv.tar.gz $argv;
end

function mktbz -d "Create a tar bz2 archive from a file or directory"
  tar cvjf  $argv.tar.bz2 $argv;
end

function findus -d "Recursively find string in files"
  find . -type f -exec grep -l $argv '{}' \;
end

function lookup --argument file
  if [ (count $argv) -ne 1 ]
    echo "Usage: $_ <file>"
    return 1
  end

  pushd .
  while [ (pwd) != '/' ]
    if [ -e "$file" ]
      pwd
      popd
      return 0
    end
    cd ..
  end
  popd
  return 1
end

function bucket_dirs
    for d in */;
        set -l name (string replace -r '/$' '' "$d");
        set -l first (string sub -l 1 "$name");
        if string match -qr '^[0-9]' "$first";
            set bucket "0-9";
        else if string match -qr '^[a-zA-Z]' "$first";
            set bucket (string lower "$first");
        else;
            set bucket "#";
        end;
    mkdir -p "$bucket";
    mv "$name" "$bucket/";
    end
end


function unrar_all --description "Extract all RAR files in subdirectories and clean up parts"
    for dir in */
        set dir (string trim --right --chars=/ $dir)

        for rar in $dir/*.rar
            if test -f "$rar"
                echo "Extracting: $rar"

                unrar x -o+ "$rar" "$dir/"

                if test $status -eq 0
                    echo "  ✓ Success — cleaning up RAR parts..."

                    # Use find to avoid glob failures when some patterns don't match
                    find $dir -maxdepth 1 -type f \( -name "*.rar" -o -name "*.r[0-9][0-9]" -o -name "*.r[1-9][0-9][0-9]" \) -delete

                    echo "  ✓ Cleaned up"
                else
                    echo "  ✗ Failed — keeping files"
                end
            end
        end
    end
end

#################################
### ENCRYPTION
#################################

function age-encrypt
    set infile $argv[1]

    if not set -q argv[1]
        echo "Usage: age-encrypt <file>"
        return 1
    end

    if not test -f $infile
        echo "Error: File not found: $infile"
        return 1
    end

    # Find all age identity files in ~/.keys
    set identities (find ~/.keys -name "*.txt" -exec grep -l "AGE-SECRET-KEY-" {} \; 2>/dev/null)

    if test (count $identities) -eq 0
        echo "No age identity files found in ~/.keys"
        return 1
    end

    # If only one identity, use it automatically
    if test (count $identities) -eq 1
        set identity $identities[1]
        echo "Using identity: "(basename $identity)
    else
        # Multiple identities: show menu
        echo "Available identities:"
        for i in (seq (count $identities))
            set pubkey (sed -n 's/# public key: //p' $identities[$i])
            echo "  $i) "(basename $identities[$i])" ($pubkey)"
        end

        read -P "Select identity (1-"(count $identities)"): " choice

        if not string match -qr '^[0-9]+$' $choice; or test $choice -lt 1; or test $choice -gt (count $identities)
            echo "Invalid selection"
            return 1
        end

        set identity $identities[$choice]
    end

    set outfile "$infile.age"
    set pubkey (sed -n 's/# public key: //p' $identity)
    age -r $pubkey -o $outfile $infile
    echo "Encrypted to $outfile using "(basename $identity)
end

function age-decrypt
    set infile $argv[1]

    if not set -q argv[1]
        echo "Usage: age-decrypt <file.age>"
        return 1
    end

    if not test -f $infile
        echo "Error: File not found: $infile"
        return 1
    end

    # Find all age identity files in ~/.keys
    set identities (find ~/.keys -name "*.txt" -exec grep -l "AGE-SECRET-KEY-" {} \; 2>/dev/null)

    if test (count $identities) -eq 0
        echo "No age identity files found in ~/.keys"
        return 1
    end

    # If only one identity, use it automatically
    if test (count $identities) -eq 1
        set identity $identities[1]
        echo "Using identity: "(basename $identity)
    else
        # Multiple identities: show menu
        echo "Available identities:"
        for i in (seq (count $identities))
            set pubkey (sed -n 's/# public key: //p' $identities[$i])
            echo "  $i) "(basename $identities[$i])" ($pubkey)"
        end

        read -P "Select identity (1-"(count $identities)"): " choice

        if not string match -qr '^[0-9]+$' $choice; or test $choice -lt 1; or test $choice -gt (count $identities)
            echo "Invalid selection"
            return 1
        end

        set identity $identities[$choice]
    end

    set outfile (string replace -r '\.age$' '' $infile)
    age -d -i $identity -o $outfile $infile
    echo "Decrypted to $outfile using "(basename $identity)
end

function gpg-encrypt --description "Encrypt a file using gpg"
  gpg --symmetric --cipher-algo AES256 $argv
end

function gpg-decrypt --description "Decrypt a file using gpg"
  gpg --decrypt $argv
end

#################################
### PIPE CONTROL
#################################

function fish_user_key_bindings
    bind \r 'replace_then_execute'
end

function replace_then_execute
    set -l new_command ( \
        commandline \
            | sed 's/ G / | grep /g' \
            | sed 's/ H$/ | head/g' \
    )
    commandline -r $new_command
    commandline -f execute
end

#################################
### GIT
#################################

function current_branch
  echo (git branch | grep \* | sed 's/* //')
end

function current_repository
  set ref (git symbolic-ref HEAD 2> /dev/null);
  or set ref (git rev-parse --short HEAD 2> /dev/null);
  or return
  echo (git remote -v | cut -d':' -f 2)
end

#################################
### NETWORKING
#################################

# EXTERNAL IP
alias myip="curl -s checkip.dyndns.org | grep -Eo '[0-9\.]+'"

# WHOIS
alias whois="whois -h whois-servers.net"

# View HTTP traffic
alias sniff="sudo ngrep -d 'en1' -t '^(GET|POST) ' 'tcp and port 80'"
alias httpdump="sudo tcpdump -i en1 -n -s 0 -w - | grep -a -o -E \"Host\: .*|GET \/.*\""

#  DIG
function digga --description "All the dig info"
  dig +nocmd $argv[1] any +multiline +noall +answer
end


################################
###  SYSTEM TOOLS
################################

# Trim new lines and copy to clipboard
alias c="tr -d '\n' | pbcopy"

# File size
alias fs="stat -f \"%z bytes\""

# Auto list directory contens on entering
function cd --description "auto ls for each cd"
  if [ -n $argv[1] ]
    builtin cd $argv[1]
    and lsd -AF
  else
    builtin cd ~
    and lsd -AF
  end
end

function ppkill --description "kill -9 a process interactively"
  _fzf_search_processes | xargs kill -KILL
end

function pgrep --description "pgrep a process interactively"
  _fzf_search_processes
end

################################
### CSV
################################

function pretty-csv
    column -t -s, $argv | less -F -S -X -K
end

function extractCol --description "Extract a CSV column by header name and copy it to the clipboard"
    if test (count $argv) -lt 1
        echo "Usage: extractCol <column_name> [csv_file]"
        echo "  If no CSV file is provided, reads from stdin"
        return 1
    end

    set -l col_name $argv[1]
    set -l csv_file

    if test (count $argv) -ge 2
        set csv_file $argv[2]
    end

    set -l awk_script '
BEGIN { FPAT = "([^,]*)|(\"[^\"]*\")"; col_idx = -1 }
NR == 1 {
    for (i = 1; i <= NF; i++) {
        gsub(/^"|"$/, "", $i)
        if ($i == col_name) {
            col_idx = i
            break
        }
    }
    if (col_idx == -1) {
        print "Error: Column \047" col_name "\047 not found in CSV header" > "/dev/stderr"
        exit 1
    }
    next
}
{
    if (col_idx <= NF) {
        val = $col_idx
        gsub(/^"|"$/, "", val)
        print val
    }
}
'

    set -l result
    if test -n "$csv_file"
        if not test -f "$csv_file"
            echo "Error: File '$csv_file' not found" >&2
            return 1
        end
        set result (awk -v col_name="$col_name" "$awk_script" "$csv_file")
    else
        set result (awk -v col_name="$col_name" "$awk_script")
    end

    if test $status -ne 0
        return 1
    end

    if type -q wl-copy
        printf "%s\n" $result | wl-copy
    else if type -q xclip
        printf "%s\n" $result | xclip -selection clipboard
    else if type -q xsel
        printf "%s\n" $result | xsel --clipboard --input
    else if type -q pbcopy
        printf "%s\n" $result | pbcopy
    else
        echo "Error: No clipboard tool found (tried: wl-copy, xclip, xsel, pbcopy)" >&2
        echo "Install one or pipe output manually: extractCol status < file.csv" >&2
        printf "%s\n" $result
        return 1
    end

    echo "Copied "(count $result)" value(s) from column '$col_name' to clipboard"
end

# function db-head
#     parquet-tools csv $HOME/code/estraven/db/$argv.parquet > /tmp/$argv.csv && bat --force-colorization --style plain /tmp/$argv.csv | column -s, -t | bat --wrap never --style grid --pager="less -RF --header 2"
# end

# function db-head-t
#     parquet-tools csv $HOME/code/estraven/db/$argv.parquet | csvtool transpose -  > /tmp/$argv.csv && bat --force-colorization --style plain /tmp/$argv.csv |  column -s, -t | bat --wrap never --style grid --pager="less -RF --header 2"
# end

################################
### PYTHON
################################

function workon
          set --function cwd (pwd)
          set --function home (dirname (realpath $HOME))
          set --function venv_path ""
          # Recursive search upward for .venv directory
          while test -n $cwd -a $home != $cwd
                  if test -e $cwd/.venv
                          set --function venv_path (realpath $cwd/.venv)
                          break
                      end
                  set --function cwd (dirname $cwd)
              end
          if test -n $venv_path
                  if test -d $venv_path
                          source $venv_path/bin/activate.fish
                      else
                          echo "Found .venv at $venv_path, but it is not a valid directory"
                      end
              else
                  echo "Could not find .venv directory"
              end
  end
