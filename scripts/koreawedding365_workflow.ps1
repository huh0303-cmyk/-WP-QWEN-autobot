param(
  [ValidateSet('status','begin','complete')]
  [string]$Action='status',
  [int]$Step=-1,
  [string]$Evidence=''
)
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
$statePath=Join-Path $root 'data\affiliate\koreawedding365-workflow-state.json'
$state=Get-Content $statePath -Raw -Encoding UTF8 | ConvertFrom-Json
if($Action -eq 'status'){
  Write-Output ("SITE={0} STEP={1} NAME={2} STATUS={3} AFFILIATE_LOCKED={4}" -f $state.site,$state.current_step,$state.current_step_name,$state.status,$state.affiliate_insertion_locked)
  $state.steps | ForEach-Object { Write-Output ("{0}: {1} [{2}]" -f $_.id,$_.name,$_.status) }
  exit 0
}
if($Step -lt 0){throw 'Specify -Step with the exact current step number.'}
if($Step -ne [int]$state.current_step){throw ("Sequential guard: current step is {0}, requested {1}." -f $state.current_step,$Step)}
if($Action -eq 'begin'){
  if($state.steps[$Step].status -eq 'completed'){throw 'This step is already completed.'}
  $state.steps[$Step].status='in_progress'
  $state.status='in_progress'
  $state | ConvertTo-Json -Depth 12 | Set-Content $statePath -Encoding UTF8
  Write-Output ("STARTED step {0}: {1}" -f $Step,$state.current_step_name)
  exit 0
}
if([string]::IsNullOrWhiteSpace($Evidence)){throw 'Completion requires a repository-relative evidence path.'}
$evidenceFull=Join-Path $root $Evidence
if(-not (Test-Path $evidenceFull)){throw ("Evidence file not found: {0}" -f $Evidence)}
if($Step -eq 6 -and (($state.steps | Where-Object {$_.id -le 5 -and $_.status -ne 'completed'}).Count -gt 0)){throw 'Affiliate insertion blocked: steps 0-5 must all be completed.'}
$state.steps[$Step].status='completed'
$state.steps[$Step].evidence=@($state.steps[$Step].evidence)+@($Evidence)
$next=$Step+1
if($next -lt $state.steps.Count){
  $state.current_step=$next
  $state.current_step_name=$state.steps[$next].name
  if($next -ge 6 -and (($state.steps | Where-Object {$_.id -le 5 -and $_.status -ne 'completed'}).Count -gt 0)){
    $state.steps[$next].status='locked'
    $state.affiliate_insertion_locked=$true
  } else {
    if($state.steps[$next].status -eq 'locked'){$state.steps[$next].status='pending'}
    $state.affiliate_insertion_locked=($next -lt 6)
  }
  $state.status='pending'
} else {$state.status='completed'}
$state.updated_at_kst=(Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
$state | ConvertTo-Json -Depth 12 | Set-Content $statePath -Encoding UTF8
Write-Output ("COMPLETED step {0}; next={1} {2}; affiliate_locked={3}" -f $Step,$state.current_step,$state.current_step_name,$state.affiliate_insertion_locked)
