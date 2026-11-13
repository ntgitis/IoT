package com.example.smartagriculture.data.remote

import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit

object RetrofitClient {
    // ⚠️ Chú ý khi mang đi báo cáo/demo:
    // - Dùng máy ảo Android Emulator trên laptop: "http://10.0.2.2:8000/"
    // - Dùng điện thoại thật: IP Wi-Fi hiện tại của laptop là "http://172.20.10.2:8000/"
    private const val BASE_URL = "http://172.20.10.2:8000/"

    private val okHttpClient = OkHttpClient.Builder()
        .connectTimeout(5, TimeUnit.SECONDS)
        .readTimeout(5, TimeUnit.SECONDS)
        .addInterceptor(HttpLoggingInterceptor().apply {
            level = HttpLoggingInterceptor.Level.BODY
        })
        .build()

    val apiService: FarmApiService by lazy {
        Retrofit.Builder()
            .baseUrl(BASE_URL)
            .client(okHttpClient)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(FarmApiService::class.java)
    }
}

