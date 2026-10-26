<?php
// Whitelist job PySpark/MapReduce di WSL (pindahan $JOBS di jobs.php). DS diganti dataset.
return [
    'run_dir' => 'C:/Temp/bigdata-web', // tanpa spasi dan '&' (cmd.exe); = /mnt/c/Temp/bigdata-web di WSL
    'repo' => '~/tugas-akhir-bigdata',
    'repo_unc' => '//wsl.localhost/Ubuntu/home/lenovo/tugas-akhir-bigdata',
    'vault_doc' => 'D:/Kuliah/Big Data & Analitik/Vault Tugas Akhir/01-Projects/Tugas-Akhir/references/peta-kode-spark.md',
    'jobs' => [
        'hdfs'      => 'hdfs dfs -du -s -h /data/raw/crime /data/raw/crashes /data/raw/311',
        'prep'      => 'bash src/mr/run_prep.sh DS',
        'parquet'   => '.venv/bin/python -m src.load_parquet DS',
        'pipeline'  => 'bash src/pipeline.sh DS',
        'bi'        => '.venv/bin/python -m src.bi',
        'mapreduce' => 'bash src/mr/run_mr.sh',
        'analisis'  => '.venv/bin/python -m src.analisis',
        'ml'        => '.venv/bin/python -m src.ml',
        'export'    => '.venv/bin/python -m src.export_web',
    ],
];
