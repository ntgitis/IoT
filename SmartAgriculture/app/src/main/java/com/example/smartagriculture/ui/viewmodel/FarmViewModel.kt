package com.example.smartagriculture.ui.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.smartagriculture.data.model.ControlRequest
import com.example.smartagriculture.data.model.CropProfile
import com.example.smartagriculture.data.model.HistoryLogItem
import com.example.smartagriculture.data.model.HistoryResponse
import com.example.smartagriculture.data.model.LatestStatusResponse
import com.example.smartagriculture.data.remote.FarmWebSocketManager
import com.example.smartagriculture.data.remote.RetrofitClient
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch

data class FarmUiState(
    val isLoading: Boolean = true,
    val errorMessage: String? = null,
    val sensorData: LatestStatusResponse? = null,
    val cropList: List<CropProfile> = emptyList(),
    val isAutoMode: Boolean = true,
    val isPumpOn: Boolean = false,
    val isLightOn: Boolean = false,
    val isLiveWebSocket: Boolean = false
)

class FarmViewModel : ViewModel() {

    private val _uiState = MutableStateFlow(FarmUiState())
    val uiState: StateFlow<FarmUiState> = _uiState.asStateFlow()

    private val _historyLogs = MutableStateFlow<List<HistoryLogItem>>(emptyList())
    val historyLogs: StateFlow<List<HistoryLogItem>> = _historyLogs.asStateFlow()

    private val _isHistoryLoading = MutableStateFlow(false)
    val isHistoryLoading: StateFlow<Boolean> = _isHistoryLoading.asStateFlow()

    private var webSocketManager: FarmWebSocketManager? = null

    init {
        fetchCropProfiles()
        setupWebSocket()
        startPeriodicDataPolling()
    }

    // Kết nối WebSocket để nhận dữ liệu đẩy thời gian thực tức thì (< 100ms)
    private fun setupWebSocket() {
        webSocketManager = FarmWebSocketManager(
            onDataReceived = { liveData ->
                viewModelScope.launch {
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        errorMessage = null,
                        sensorData = liveData,
                        isAutoMode = liveData.mode == "AUTO",
                        isPumpOn = liveData.pumpStatus == "ON",
                        isLightOn = liveData.lightStatus == "ON",
                        isLiveWebSocket = true
                    )
                }
            },
            onConnectionStatusChanged = { isConnected ->
                viewModelScope.launch {
                    _uiState.value = _uiState.value.copy(isLiveWebSocket = isConnected)
                }
            }
        )
        webSocketManager?.connect()
    }

    // 1. Tự động lấy dữ liệu định kỳ dự phòng (nếu WebSocket mất kết nối)
    private fun startPeriodicDataPolling() {
        viewModelScope.launch {
            while (isActive) {
                // Nếu WebSocket đang hoạt động ổn định thì giảm tần suất polling xuống để tiết kiệm pin
                if (!_uiState.value.isLiveWebSocket) {
                    fetchLatestStatus()
                }
                delay(3000)
            }
        }
    }

    override fun onCleared() {
        super.onCleared()
        webSocketManager?.close()
    }

    fun fetchLatestStatus() {
        viewModelScope.launch {
            try {
                val response = RetrofitClient.apiService.getLatestStatus()
                if (response.isSuccessful && response.body() != null) {
                    val data = response.body()!!
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        errorMessage = null,
                        sensorData = data,
                        isAutoMode = data.mode == "AUTO",
                        isPumpOn = data.pumpStatus == "ON",
                        isLightOn = data.lightStatus == "ON"
                    )
                } else {
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        errorMessage = "Không nhận được phản hồi từ máy chủ"
                    )
                }
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    errorMessage = "Lỗi kết nối Server: ${e.localizedMessage}"
                )
            }
        }
    }

    // Lấy lịch sử đo đạc để vẽ biểu đồ
    fun fetchHistory(limit: Int = 30) {
        viewModelScope.launch {
            _isHistoryLoading.value = true
            try {
                val res = RetrofitClient.apiService.getHistory(limit)
                if (res.isSuccessful && res.body() != null) {
                    _historyLogs.value = res.body()!!.data
                }
            } catch (e: Exception) {
                // Giữ nguyên dữ liệu cũ nếu lỗi mạng
            } finally {
                _isHistoryLoading.value = false
            }
        }
    }

    // 2. Lấy danh sách cây trồng
    fun fetchCropProfiles() {
        viewModelScope.launch {
            try {
                val res = RetrofitClient.apiService.getCropProfiles()
                if (res.isSuccessful && res.body() != null) {
                    _uiState.value = _uiState.value.copy(cropList = res.body()!!.crops)
                }
            } catch (_: Exception) {}
        }
    }

    // 3. Chuyển đổi chế độ TỰ ĐỘNG (AUTO) / THỦ CÔNG (MANUAL)
    fun setSystemMode(isAuto: Boolean) {
        val newMode = if (isAuto) "AUTO" else "MANUAL"
        viewModelScope.launch {
            try {
                val req = ControlRequest(mode = newMode)
                RetrofitClient.apiService.sendControlCommand(req)
                fetchLatestStatus()
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(errorMessage = "Lỗi chuyển chế độ: ${e.message}")
            }
        }
    }

    // 4. Bật / Tắt Máy Bơm bằng tay (chỉ khi đang ở MANUAL)
    fun togglePump(targetOn: Boolean) {
        val cmd = if (targetOn) "ON" else "OFF"
        viewModelScope.launch {
            try {
                val req = ControlRequest(mode = "MANUAL", manualPump = cmd)
                RetrofitClient.apiService.sendControlCommand(req)
                fetchLatestStatus()
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(errorMessage = "Lỗi điều khiển bơm: ${e.message}")
            }
        }
    }

    // 5. Bật / Tắt Đèn Quang Hợp bằng tay (chỉ khi đang ở MANUAL)
    fun toggleLight(targetOn: Boolean) {
        val cmd = if (targetOn) "ON" else "OFF"
        viewModelScope.launch {
            try {
                val req = ControlRequest(mode = "MANUAL", manualLight = cmd)
                RetrofitClient.apiService.sendControlCommand(req)
                fetchLatestStatus()
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(errorMessage = "Lỗi điều khiển đèn: ${e.message}")
            }
        }
    }

    // 6. Chọn hồ sơ cây trồng (Cà chua, Dưa lưới, v.v.)
    fun selectCrop(cropId: String) {
        val currentMode = if (_uiState.value.isAutoMode) "AUTO" else "MANUAL"
        viewModelScope.launch {
            try {
                val req = ControlRequest(mode = currentMode, activeCrop = cropId)
                RetrofitClient.apiService.sendControlCommand(req)
                fetchLatestStatus()
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(errorMessage = "Lỗi chọn cây: ${e.message}")
            }
        }
    }
}

