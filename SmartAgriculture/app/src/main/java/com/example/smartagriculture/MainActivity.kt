package com.example.smartagriculture

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.viewModels
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Surface
import androidx.compose.ui.Modifier
import com.example.smartagriculture.ui.screens.MainScreen
import com.example.smartagriculture.ui.theme.SmartAgricultureTheme
import com.example.smartagriculture.ui.viewmodel.FarmViewModel

class MainActivity : ComponentActivity() {
    private val viewModel: FarmViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            SmartAgricultureTheme {
                Surface(
                    modifier = Modifier.fillMaxSize()
                ) {
                    MainScreen(viewModel = viewModel)
                }
            }
        }
    }
}
