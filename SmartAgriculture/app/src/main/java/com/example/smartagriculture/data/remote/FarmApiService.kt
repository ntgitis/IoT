package com.example.smartagriculture.data.remote

import com.example.smartagriculture.data.model.*
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Query

interface FarmApiService {

    // Lấy thông số mới nhất khi mở app
    @GET("api/latest-status")
    suspend fun getLatestStatus(): Response<LatestStatusResponse>

    // Gửi lệnh điều khiển bật/tắt bơm, đèn, đổi mode
    @POST("api/control")
    suspend fun sendControlCommand(@Body request: ControlRequest): Response<GeneralApiResponse>

    // Lấy danh sách cây trồng
    @GET("api/crops")
    suspend fun getCropProfiles(): Response<CropListResponse>

    // Lấy lịch sử đo đạc để vẽ biểu đồ
    @GET("api/history")
    suspend fun getHistory(@Query("limit") limit: Int = 30): Response<HistoryResponse>
}
