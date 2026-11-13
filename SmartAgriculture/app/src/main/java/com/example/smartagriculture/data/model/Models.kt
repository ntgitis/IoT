package com.example.smartagriculture.data.model

import com.google.gson.annotations.SerializedName

// Model nhận dữ liệu trạng thái đầy đủ từ Backend
data class LatestStatusResponse(
    @SerializedName("status") val status: String,
    @SerializedName("timestamp") val timestamp: String?,
    @SerializedName("mode") val mode: String,                // "AUTO" hoặc "MANUAL"
    @SerializedName("active_crop") val activeCrop: String,
    @SerializedName("crop_name") val cropName: String,
    @SerializedName("air_temp") val airTemp: Float,
    @SerializedName("air_hum") val airHum: Float,
    @SerializedName("soil_temp") val soilTemp: Float,
    @SerializedName("soil_moisture") val soilMoisture: Int,
    @SerializedName("lux") val lux: Float,
    @SerializedName("vpd") val vpd: Float?,
    @SerializedName("pump_status") val pumpStatus: String,   // "ON" hoặc "OFF"
    @SerializedName("light_status") val lightStatus: String, // "ON" hoặc "OFF"
    @SerializedName("manual_pump") val manualPump: String,
    @SerializedName("manual_light") val manualLight: String,
    @SerializedName("lux_threshold") val luxThreshold: Float
)

// Model gửi lệnh điều khiển từ App lên Server
data class ControlRequest(
    @SerializedName("mode") val mode: String,                       // "AUTO" hoặc "MANUAL"
    @SerializedName("manual_pump") val manualPump: String? = null,  // "ON" hoặc "OFF"
    @SerializedName("manual_light") val manualLight: String? = null,// "ON" hoặc "OFF"
    @SerializedName("lux_threshold") val luxThreshold: Float? = null,
    @SerializedName("active_crop") val activeCrop: String? = null
)

// Model thông tin cây trồng
data class CropProfile(
    @SerializedName("id") val id: String,
    @SerializedName("name") val name: String,
    @SerializedName("min_soil_moisture") val minSoilMoisture: Int,
    @SerializedName("optimal_soil_moisture") val optimalSoilMoisture: Int,
    @SerializedName("max_soil_moisture") val maxSoilMoisture: Int,
    @SerializedName("min_lux") val minLux: Int,
    @SerializedName("description") val description: String
)

data class CropListResponse(
    @SerializedName("status") val status: String,
    @SerializedName("crops") val crops: List<CropProfile>
)

// Model phản hồi chung
data class GeneralApiResponse(
    @SerializedName("status") val status: String,
    @SerializedName("message") val message: String?
)

// Model phần tử lịch sử đo đạc
data class HistoryLogItem(
    @SerializedName("id") val id: Int,
    @SerializedName("timestamp") val timestamp: String?,
    @SerializedName("air_temp") val airTemp: Float,
    @SerializedName("air_hum") val airHum: Float,
    @SerializedName("soil_temp") val soilTemp: Float,
    @SerializedName("soil_moisture") val soilMoisture: Int,
    @SerializedName("lux") val lux: Float,
    @SerializedName("vpd") val vpd: Float?,
    @SerializedName("pump_status") val pumpStatus: String,
    @SerializedName("light_status") val lightStatus: String
)

data class HistoryResponse(
    @SerializedName("status") val status: String,
    @SerializedName("count") val count: Int,
    @SerializedName("data") val data: List<HistoryLogItem>
)

