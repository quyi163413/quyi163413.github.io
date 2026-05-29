package com.iptv.player

data class Channel(
    val name: String,
    val url: String,
    val group: String = "",
    val tvgId: String = "",
    val tvgLogo: String = ""
)
