Try {
    pip -V
    pip install virtualenv
} Catch {
    pip3 install virtualenv
}

If (Test-Path venv-sitegeist){
    .\venv-sitegeist\Scripts\activate
} Else {
    virtualenv venv-sitegeist
    .\venv-sitegeist\Scripts\activate
    .\setup.ps1
}