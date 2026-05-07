package com.example.app.service;

import org.springframework.stereotype.Service;

@Service
public class AppService {
    public String status() {
        return "Project is running - Project Agent Generated Starter v1";
    }
}
