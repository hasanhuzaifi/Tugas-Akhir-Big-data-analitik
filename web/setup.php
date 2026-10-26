<?php
require __DIR__ . '/lib.php';
$l = import_all(__DIR__ . '/data');
echo implode("\n", $l), "\nOK\n";
