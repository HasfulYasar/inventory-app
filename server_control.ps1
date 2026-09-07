Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$serviceName = "ShowCashApp"

$form = New-Object System.Windows.Forms.Form
$form.Text = "ShowCash Server Control"
$form.Size = New-Object System.Drawing.Size(320, 260)
$form.StartPosition = "CenterScreen"
$form.FormBorderStyle = "FixedDialog"
$form.MaximizeBox = $false

$statusLabel = New-Object System.Windows.Forms.Label
$statusLabel.Location = New-Object System.Drawing.Point(20, 20)
$statusLabel.Size = New-Object System.Drawing.Size(280, 30)
$statusLabel.Font = New-Object System.Drawing.Font("Segoe UI", 12, [System.Drawing.FontStyle]::Bold)
$form.Controls.Add($statusLabel)

function Update-Status {
    try {
        $svc = Get-Service -Name $serviceName -ErrorAction Stop
        $statusLabel.Text = "Status: $($svc.Status)"
        if ($svc.Status -eq "Running") {
            $statusLabel.ForeColor = [System.Drawing.Color]::Green
        } else {
            $statusLabel.ForeColor = [System.Drawing.Color]::Red
        }
    } catch {
        $statusLabel.Text = "Status: Not found"
        $statusLabel.ForeColor = [System.Drawing.Color]::Gray
    }
}

$startBtn = New-Object System.Windows.Forms.Button
$startBtn.Text = "Start Server"
$startBtn.Location = New-Object System.Drawing.Point(20, 70)
$startBtn.Size = New-Object System.Drawing.Size(260, 40)
$startBtn.BackColor = [System.Drawing.Color]::LightGreen
$startBtn.Add_Click({
    Start-Service -Name $serviceName -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 1
    Update-Status
})
$form.Controls.Add($startBtn)

$stopBtn = New-Object System.Windows.Forms.Button
$stopBtn.Text = "Stop Server"
$stopBtn.Location = New-Object System.Drawing.Point(20, 120)
$stopBtn.Size = New-Object System.Drawing.Size(260, 40)
$stopBtn.BackColor = [System.Drawing.Color]::LightCoral
$stopBtn.Add_Click({
    Stop-Service -Name $serviceName -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 1
    Update-Status
})
$form.Controls.Add($stopBtn)

$restartBtn = New-Object System.Windows.Forms.Button
$restartBtn.Text = "Restart Server"
$restartBtn.Location = New-Object System.Drawing.Point(20, 170)
$restartBtn.Size = New-Object System.Drawing.Size(260, 40)
$restartBtn.BackColor = [System.Drawing.Color]::LightYellow
$restartBtn.Add_Click({
    Restart-Service -Name $serviceName -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 1
    Update-Status
})
$form.Controls.Add($restartBtn)

Update-Status
[System.Windows.Forms.Application]::Run($form)
