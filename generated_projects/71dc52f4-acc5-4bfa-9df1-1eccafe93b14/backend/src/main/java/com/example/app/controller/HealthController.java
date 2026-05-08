package com.example.app.controller;

import com.example.app.service.AppService;
import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class HealthController {
    private final AppService appService;

    public HealthController(AppService appService) {
        this.appService = appService;
    }

    @GetMapping("/")
    public Map<String, String> status() {
        return Map.of("status", "ok", "message", "Project is running", "version", "Project Agent Generated Starter v1");
    }
}
