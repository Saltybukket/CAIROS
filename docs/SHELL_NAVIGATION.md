# Shell Navigation

A child process cannot permanently change the parent shell's working directory.
That is a shell limitation, not a CAIROS bug.

CAIROS can search for a directory and print paths:

```bash
cairos find-dir TU-Graz
cairos find-dir "my folder" --max-depth 4 --from .
cairos find-dir TU-Graz --exact
```

Natural-language guidance is shell-aware:

```cmd
cairos plan go into the directory TU-Graz. mind that you are in windows cmd
```

## Wrappers

cmd.exe:

```cmd
for /f "delims=" %i in ('cairos find-dir TU-Graz') do cd /d "%i"
```

PowerShell:

```powershell
function cairoscd($name) {
  $p = cairos find-dir $name
  if ($LASTEXITCODE -eq 0 -and $p) { Set-Location $p }
}
```

bash/zsh:

```bash
cairoscd() {
  local p
  p="$(cairos find-dir "$1")" || return
  cd "$p"
}
```

If multiple directories match, CAIROS prints choices so you can pick the right
path.
