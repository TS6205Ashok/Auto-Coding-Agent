package com.example.app.repository;

import com.example.app.model.AppModel;
import java.util.List;
import org.springframework.stereotype.Repository;

@Repository
public class AppRepository {
    public List<AppModel> findAll() {
        return List.of();
    }
}
