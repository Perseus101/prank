script_dir=$(dirname -- "$(readlink -f -- "$BASH_SOURCE")")
cd "$script_dir"

aplay napalm_death_you_suffer.wav
date >> log.txt
