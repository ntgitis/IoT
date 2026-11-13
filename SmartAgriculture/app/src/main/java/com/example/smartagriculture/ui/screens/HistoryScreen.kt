package com.example.smartagriculture.ui.screens

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.ShowChart
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.smartagriculture.data.model.HistoryLogItem
import com.example.smartagriculture.ui.viewmodel.FarmViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HistoryScreen(viewModel: FarmViewModel) {
    val historyList by viewModel.historyLogs.collectAsState()
    val isLoading by viewModel.isHistoryLoading.collectAsState()

    LaunchedEffect(Unit) {
        viewModel.fetchHistory()
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Lịch Sử & Xu Hướng", fontWeight = FontWeight.Bold) },
                actions = {
                    IconButton(onClick = { viewModel.fetchHistory() }) {
                        Icon(Icons.Default.Refresh, contentDescription = "Làm mới")
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.primaryContainer
                )
            )
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            // 1. BIỂU ĐỒ ĐƯỜNG NATIVE (SOIL MOISTURE TREND)
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text("BIẾN THIÊN ĐỘ ẨM ĐẤT (%)", fontSize = 12.sp, fontWeight = FontWeight.Bold, color = Color.Gray)
                        Icon(Icons.Default.ShowChart, contentDescription = null, tint = Color(0xFF1E88E5))
                    }

                    Spacer(modifier = Modifier.height(16.dp))

                    if (historyList.isNotEmpty()) {
                        val moisturePoints = historyList.map { it.soilMoisture.toFloat() }
                        SimpleLineChart(
                            points = moisturePoints,
                            lineColor = Color(0xFF1E88E5),
                            fillColor = Color(0x331E88E5),
                            minY = 0f,
                            maxY = 100f,
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(140.dp)
                        )
                    } else {
                        Box(
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(140.dp),
                            contentAlignment = Alignment.Center
                        ) {
                            Text("Chưa có đủ dữ liệu để vẽ biểu đồ", fontSize = 13.sp, color = Color.Gray)
                        }
                    }
                }
            }

            // 2. DANH SÁCH NHẬT KÝ ĐO ĐẠC GẦN ĐÂY
            Text("Nhật ký chi tiết", fontWeight = FontWeight.Bold, fontSize = 16.sp)

            if (isLoading) {
                Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    CircularProgressIndicator()
                }
            } else {
                LazyColumn(
                    modifier = Modifier.fillMaxSize(),
                    verticalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    items(historyList) { item ->
                        HistoryItemCard(item)
                    }
                }
            }
        }
    }
}

@Composable
fun SimpleLineChart(
    points: List<Float>,
    lineColor: Color,
    fillColor: Color,
    minY: Float,
    maxY: Float,
    modifier: Modifier = Modifier
) {
    Canvas(modifier = modifier) {
        if (points.size < 2) return@Canvas

        val width = size.width
        val height = size.height
        val stepX = width / (points.size - 1)

        val path = Path()
        val fillPath = Path()

        points.forEachIndexed { index, value ->
            val normalizedY = 1f - ((value - minY) / (maxY - minY)).coerceIn(0f, 1f)
            val x = index * stepX
            val y = normalizedY * height

            if (index == 0) {
                path.moveTo(x, y)
                fillPath.moveTo(x, height)
                fillPath.lineTo(x, y)
            } else {
                path.lineTo(x, y)
                fillPath.lineTo(x, y)
            }
        }

        fillPath.lineTo(width, height)
        fillPath.close()

        // Vẽ mảng bóng mờ dưới đường
        drawPath(path = fillPath, color = fillColor)
        // Vẽ đường viền
        drawPath(path = path, color = lineColor, style = Stroke(width = 3.dp.toPx()))

        // Vẽ các chấm điểm mốc
        points.forEachIndexed { index, value ->
            val normalizedY = 1f - ((value - minY) / (maxY - minY)).coerceIn(0f, 1f)
            val x = index * stepX
            val y = normalizedY * height
            drawCircle(color = lineColor, radius = 3.dp.toPx(), center = Offset(x, y))
        }
    }
}

@Composable
fun HistoryItemCard(item: HistoryLogItem) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(10.dp)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(12.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column {
                Text(
                    text = item.timestamp?.substringAfter("T")?.substringBefore(".") ?: "--:--:--",
                    fontSize = 11.sp,
                    color = Color.Gray
                )
                Text("Ẩm đất: ${item.soilMoisture}% | Khí: ${item.airTemp}°C", fontWeight = FontWeight.SemiBold, fontSize = 14.sp)
            }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                StatusBadge(label = "Bơm", state = item.pumpStatus, activeColor = Color(0xFF1E88E5))
                StatusBadge(label = "Đèn", state = item.lightStatus, activeColor = Color(0xFFFBC02D))
            }
        }
    }
}

@Composable
fun StatusBadge(label: String, state: String, activeColor: Color) {
    val isActive = state == "ON"
    Surface(
        color = if (isActive) activeColor.copy(alpha = 0.2f) else Color(0xFFE0E0E0),
        shape = RoundedCornerShape(6.dp)
    ) {
        Text(
            text = "$label: $state",
            color = if (isActive) activeColor else Color.Gray,
            fontSize = 11.sp,
            fontWeight = FontWeight.Bold,
            modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
        )
    }
}

