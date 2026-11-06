param(
    [Parameter(Mandatory=$true)]
    [ValidatePattern('^[A-Za-z0-9_-]{1,64}$')]
    [string]$SecretName,
    [string]$Prompt = 'Enter the credential. The value is masked while typing or pasting.'
)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$form = New-Object System.Windows.Forms.Form
$form.Text = 'Encrypt and save on this PC'
$form.Size = New-Object System.Drawing.Size(590,205)
$form.StartPosition = 'CenterScreen'
$form.TopMost = $true

$label = New-Object System.Windows.Forms.Label
$label.Text = $Prompt
$label.AutoSize = $true
$label.MaximumSize = New-Object System.Drawing.Size(545,0)
$label.Location = New-Object System.Drawing.Point(16,18)
$form.Controls.Add($label)

$box = New-Object System.Windows.Forms.TextBox
$box.Location = New-Object System.Drawing.Point(18,65)
$box.Size = New-Object System.Drawing.Size(535,25)
$box.UseSystemPasswordChar = $true
$form.Controls.Add($box)

$save = New-Object System.Windows.Forms.Button
$save.Text = 'Encrypt and save on this PC'
$save.Location = New-Object System.Drawing.Point(330,112)
$save.Size = New-Object System.Drawing.Size(223,34)
$save.DialogResult = [System.Windows.Forms.DialogResult]::OK
$form.Controls.Add($save)

$cancel = New-Object System.Windows.Forms.Button
$cancel.Text = 'Cancel'
$cancel.Location = New-Object System.Drawing.Point(240,112)
$cancel.Size = New-Object System.Drawing.Size(78,34)
$cancel.DialogResult = [System.Windows.Forms.DialogResult]::Cancel
$form.Controls.Add($cancel)
$form.AcceptButton = $save
$form.CancelButton = $cancel

try {
    $result = $form.ShowDialog()
    if ($result -ne [System.Windows.Forms.DialogResult]::OK) {
        Write-Output 'CANCELLED'
        exit 0
    }

    $plain = $box.Text
    if ([string]::IsNullOrWhiteSpace($plain)) {
        [System.Windows.Forms.MessageBox]::Show('No value was entered. Nothing was saved.')
        exit 2
    }

    $directory = Join-Path $env:LOCALAPPDATA 'Korea365\Secrets'
    New-Item -ItemType Directory -Force -Path $directory | Out-Null
    $target = Join-Path $directory ($SecretName + '.dpapi')
    $secure = ConvertTo-SecureString $plain -AsPlainText -Force
    $encrypted = ConvertFrom-SecureString $secure
    [System.IO.File]::WriteAllText($target, $encrypted, [System.Text.Encoding]::UTF8)

    $box.Clear()
    $plain = $null
    $secure.Dispose()
    $secure = $null
    $encrypted = $null

    [System.Windows.Forms.MessageBox]::Show(
        'Encrypted with Windows DPAPI for this Windows user on this PC. The value was not printed.',
        'Saved'
    )
    Write-Output ('ENCRYPTED_FILE_SAVED: ' + $SecretName + '.dpapi')
}
finally {
    if ($null -ne $form) { $form.Dispose() }
}
