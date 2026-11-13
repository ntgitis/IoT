package com.example.smartagriculture.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.smartagriculture.data.model.LatestStatusResponse
import com.example.smartagriculture.ui.viewmodel.FarmViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DashboardScreen(viewModel: FarmViewModel) {
    val uiState by viewModel.uiState.collectAsState()
    var showCropDialog by remember { mutableStateOf(false) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text("Vườn Thông Minh", fontWeight = FontWeight.Bold, fontSize = 20.sp)
                        Text(
                            text = if (uiState.sensorData != null) "● Đang kết nối trực tuyến" else "○ Đang kết nối...",
                            fontSize = 12.sp,
                            color = if (uiState.sensorData != null) Color(0xFF4CAF50) else Color.Gray
                        )
                    }
                },
                actions = {
                    IconButton(onClick = { viewModel.fetchLatestStatus() }) {
                        Icon(Icons.Default.Refresh, contentDescription = "Làm mới")
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.primaryContainer
                )
            )
        }
    ) { paddingValues ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
                .padding(16.dp)
                .verticalScroll(rememberScrollState()),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            // Thông báo lỗi nếu có
            if (uiState.errorMessage != null) {
                Card(
                    colors = CardDefaults.cardColors(containerColor = Color(0xFFFFEBEE)),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Row(
                        modifier = Modifier.padding(12.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Icon(Icons.Default.Warning, contentDescription = null, tint = Color.Red)
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(uiState.errorMessage!!, color = Color.Red, fontSize = 13.sp)
                    }
                }
            }

            // 1. THANH CHỌN HỒ SƠ CÂY TRỒNG
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(12.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(14.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column {
                        Text("CÂY TRỒNG ĐANG THEO DÕI", fontSize = 11.sp, color = Color.Gray, fontWeight = FontWeight.SemiBold)
                        Text(
                            text = uiState.sensorData?.cropName ?: "Đang tải...",
                            fontSize = 17.sp,
                            fontWeight = FontWeight.Bold
                        )
                    }
                    Button(
                        onClick = { showCropDialog = true },
                        shape = RoundedCornerShape(8.dp)
                    ) {
                        Text("Đổi cây")
                    }
                }
            }

            // 2. KHỐI THÔNG SỐ CẢM BIẾN (GRID GAUGE CARDS)
            val data = uiState.sensorData
            if (data != null) {
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    SensorMetricCard(
                        modifier = Modifier.weight(1f),
                        title = "Độ ẩm đất",
                        value = "${data.soilMoisture}%",
                        status = when {
                            data.soilMoisture < 35 -> "Khô cạn"
                            data.soilMoisture > 75 -> "Quá ẩm"
                            else -> "Lý tưởng"
                        },
                        icon = Icons.Default.WaterDrop,
                        accentColor = if (data.soilMoisture < 35) Color(0xFFE53935) else Color(0xFF1E88E5)
                    )
                    SensorMetricCard(
                        modifier = Modifier.weight(1f),
                        title = "Nhiệt độ khí",
                        value = "${data.airTemp}°C",
                        status = "Ẩm: ${data.airHum}%",
                        icon = Icons.Default.Thermostat,
                        accentColor = Color(0xFFFB8C00)
                    )
                }

                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    SensorMetricCard(
                        modifier = Modifier.weight(1f),
                        title = "Ánh sáng",
                        value = "${data.lux.toInt()} Lux",
                        status = if (data.lux < 300) "Trời tối" else "Đủ sáng",
                        icon = Icons.Default.WbSunny,
                        accentColor = Color(0xFFFDD835)
                    )
                    SensorMetricCard(
                        modifier = Modifier.weight(1f),
                        title = "Nhiệt độ đất",
                        value = "${data.soilTemp}°C",
                        status = "VPD: ${data.vpd ?: 0f} kPa",
                        icon = Icons.Default.Grass,
                        accentColor = Color(0xFF43A047)
                    )
                }
            } else {
                Box(modifier = Modifier.fillMaxWidth().height(150.dp), contentAlignment = Alignment.Center) {
                    CircularProgressIndicator()
                }
            }

            // 3. KHỐI ĐIỀU KHIỂN TRỰC TIẾP (CONTROL PANEL)
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(16.dp),
                elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
            ) {
                Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column {
                            Text("CHẾ ĐỘ HỆ THỐNG", fontSize = 12.sp, color = Color.Gray, fontWeight = FontWeight.Bold)
                            Text(
                                text = if (uiState.isAutoMode) "Tự động thông minh (AI)" else "Điều khiển bằng tay (Manual)",
                                fontSize = 16.sp,
                                fontWeight = FontWeight.SemiBold,
                                color = if (uiState.isAutoMode) Color(0xFF2E7D32) else Color(0xFFE65100)
                            )
                        }
                        Switch(
                            checked = uiState.isAutoMode,
                            onCheckedChange = { isAuto -> viewModel.setSystemMode(isAuto) }
                        )
                    }

                    HorizontalDivider()

                    // Nút điều khiển Máy Bơm
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(
                                Icons.Default.PowerSettingsNew,
                                contentDescription = null,
                                tint = if (uiState.isPumpOn) Color(0xFF1E88E5) else Color.Gray
                            )
                            Spacer(modifier = Modifier.width(10.dp))
                            Column {
                                Text("Máy Bơm Nước", fontWeight = FontWeight.Medium)
                                Text(
                                    text = if (uiState.isPumpOn) "ĐANG BẬT" else "ĐANG TẮT",
                                    fontSize = 12.sp,
                                    color = if (uiState.isPumpOn) Color(0xFF1E88E5) else Color.Gray
                                )
                            }
                        }
                        Button(
                            onClick = { viewModel.togglePump(!uiState.isPumpOn) },
                            enabled = !uiState.isAutoMode, // Chỉ mở khi ở chế độ Manual
                            colors = ButtonDefaults.buttonColors(
                                containerColor = if (uiState.isPumpOn) Color(0xFFE53935) else Color(0xFF1E88E5)
                            )
                        ) {
                            Text(if (uiState.isPumpOn) "Tắt Bơm" else "Bật Bơm")
                        }
                    }

                    // Nút điều khiển Đèn Quang Hợp
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(
                                Icons.Default.Lightbulb,
                                contentDescription = null,
                                tint = if (uiState.isLightOn) Color(0xFFFBC02D) else Color.Gray
                            )
                            Spacer(modifier = Modifier.width(10.dp))
                            Column {
                                Text("Đèn Quang Hợp", fontWeight = FontWeight.Medium)
                                Text(
                                    text = if (uiState.isLightOn) "ĐANG BẬT" else "ĐANG TẮT",
                                    fontSize = 12.sp,
                                    color = if (uiState.isLightOn) Color(0xFFFBC02D) else Color.Gray
                                )
                            }
                        }
                        Button(
                            onClick = { viewModel.toggleLight(!uiState.isLightOn) },
                            enabled = !uiState.isAutoMode,
                            colors = ButtonDefaults.buttonColors(
                                containerColor = if (uiState.isLightOn) Color(0xFFE53935) else Color(0xFFFBC02D)
                            )
                        ) {
                            Text(if (uiState.isLightOn) "Tắt Đèn" else "Bật Đèn")
                        }
                    }

                    if (uiState.isAutoMode) {
                        Text(
                            text = "💡 Chuyển sang chế độ Manual nếu bạn muốn chủ động Bật/Tắt thiết bị bằng tay.",
                            fontSize = 12.sp,
                            color = Color.Gray
                        )
                    }
                }
            }
        }
    }

    // Dialog chọn loại cây trồng
    if (showCropDialog) {
        AlertDialog(
            onDismissRequest = { showCropDialog = false },
            title = { Text("Chọn Hồ Sơ Cây Trồng") },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    uiState.cropList.forEach { crop ->
                        Card(
                            onClick = {
                                viewModel.selectCrop(crop.id)
                                showCropDialog = false
                            },
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Column(modifier = Modifier.padding(12.dp)) {
                                Text(crop.name, fontWeight = FontWeight.Bold, fontSize = 15.sp)
                                Text(crop.description, fontSize = 12.sp, color = Color.Gray)
                                Spacer(modifier = Modifier.height(4.dp))
                                Text(
                                    "Ngưỡng ẩm đất: ${crop.minSoilMoisture}% - ${crop.optimalSoilMoisture}%",
                                    fontSize = 11.sp,
                                    color = MaterialTheme.colorScheme.primary
                                )
                            }
                        }
                    }
                }
            },
            confirmButton = {
                TextButton(onClick = { showCropDialog = false }) {
                    Text("Đóng")
                }
            }
        )
    }
}

@Composable
fun SensorMetricCard(
    modifier: Modifier = Modifier,
    title: String,
    value: String,
    status: String,
    icon: ImageVector,
    accentColor: Color
) {
    Card(
        modifier = modifier,
        shape = RoundedCornerShape(14.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
    ) {
        Column(modifier = Modifier.padding(14.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(title, fontSize = 12.sp, color = Color.Gray, fontWeight = FontWeight.Medium)
                Icon(icon, contentDescription = null, tint = accentColor, modifier = Modifier.size(20.dp))
            }
            Spacer(modifier = Modifier.height(8.dp))
            Text(value, fontSize = 22.sp, fontWeight = FontWeight.Bold)
            Spacer(modifier = Modifier.height(4.dp))
            Text(status, fontSize = 11.sp, color = accentColor, fontWeight = FontWeight.SemiBold)
        }
    }
}

