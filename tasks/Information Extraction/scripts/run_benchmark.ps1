param(
    [string]$Config = "configs/sroie_quick.json"
)

& ie-benchmark run --config $Config
