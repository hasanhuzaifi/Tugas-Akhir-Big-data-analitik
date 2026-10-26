<?php
use App\Http\Controllers\JobController;
use Illuminate\Support\Facades\Route;

Route::post('/jobs/{job}', [JobController::class, 'run']);
Route::get('/jobs/{job}/log', [JobController::class, 'log']);
Route::get('/kode', [JobController::class, 'kode']);
