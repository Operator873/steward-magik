# Steward-Magik
A pure Python (3.6+) script for doing sysopy/stewy things from your computer via the API. Requires an OAuth consumer be entered into a local file (see magik.conf) and saved in a specifc place. Use on your own responsibility, I'm not at fault for stupid mistakes. Please use the `--help` switch... or even better, read the code.

## Installation

1. Clone the repo to a location of your choosing
2. Add your OAuth consumer to magik.conf, rename the file and move to the location specified in the file's directions at the top.
3. Execute the script and call `--help` switch  
   1. For unix-y systems   
   ```python3 /path/to/stew-magik.py --help```  
   2. For Windohs systems  
   ```python C:\path\to\stew-magik.py --help```

### >>> Protip2
1. If you're using a unix-y system, create a soft link into your `/usr/local/bin` directory like this:  
`sudo ln -s /path/to/stew-magik.py /usr/local/bin/magik`

After that's done, you can skip the tediousness and just use it as a command:  
`magik block --target Someone --target Someone else --project somewiki --duration forever --reason I'm an asshole`

2. Enclose special characters in double quotes (`"`)
3. Get into the good habit of enclosing strings with double quotes as well.

## Usage
### Blocks
```magik block --target account1 --target account2 --project somewiki --duration 3months --reason Long term abuse```

### Reblocks
```magik block --target Someone --project somewiki --duration forever --force --revoketpa --reason Abusing talk page```

### Unblocks
```magik unblock --target account1 --target account2 --project somewiki --reason Wooppsiieee```

### Locks
```magik lock --target Snuffy --reason lta```

### Lock and hide
```magik loc --target Snuffy --reason lta --hide```

### Lock and suppress
```magik lock --target Snuffy --reason "LTA on rampage" --suppress```

### Unlocks
```magik unlock --target Snuffy --reason Not an lta```

### Global blocks
```magik gblock --target ip.add.res.1 --target ip.add.res.2 --duration 10mins --anononly --dryrun --reason I'm testing```

### Global unblocks
```magik ungblock --target ip.add.res.1 --target ip.add.res.2 --duration 10mins --reason I'm done testing```