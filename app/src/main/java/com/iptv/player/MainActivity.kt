package com.iptv.player

import android.content.Intent
import android.os.Bundle
import android.widget.*
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import androidx.preference.PreferenceManager
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class MainActivity : AppCompatActivity() {
    private lateinit var recyclerView: RecyclerView
    private lateinit var progressBar: ProgressBar
    private lateinit var errorText: TextView
    private lateinit var groupSpinner: Spinner
    
    private val allChannels = mutableListOf<Channel>()
    private var currentChannels = listOf<Channel>()
    private var groups = listOf("全部")
    private lateinit var adapter: ChannelAdapter

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        
        recyclerView = findViewById(R.id.recyclerView)
        progressBar = findViewById(R.id.progressBar)
        errorText = findViewById(R.id.errorText)
        groupSpinner = findViewById(R.id.groupSpinner)
        
        recyclerView.layoutManager = LinearLayoutManager(this)
        
        setupSettingsButton()
        loadChannels()
    }
    
    private fun setupSettingsButton() {
        // 通过 toolbar 或 actionbar 添加设置按钮，这里简化：长按标题触发
        supportActionBar?.setDisplayHomeAsUpEnabled(false)
        supportActionBar?.title = "IPTV Player"
    }
    
    override fun onOptionsItemSelected(item: android.view.MenuItem): Boolean {
        if (item.itemId == android.R.id.home) {
            onBackPressedDispatcher.onBackPressed()
            return true
        }
        return super.onOptionsItemSelected(item)
    }
    
    override fun onCreateOptionsMenu(menu: android.view.Menu?): Boolean {
        menuInflater.inflate(R.menu.main_menu, menu)
        return true
    }
    
    override fun onOptionsItemSelected(item: android.view.MenuItem): Boolean {
        if (item.itemId == R.id.action_settings) {
            startActivity(Intent(this, SettingsActivity::class.java))
            return true
        }
        return super.onOptionsItemSelected(item)
    }
    
    private fun loadChannels() {
        progressBar.visibility = View.VISIBLE
        errorText.visibility = View.GONE
        lifecycleScope.launch {
            try {
                val prefs = PreferenceManager.getDefaultSharedPreferences(this@MainActivity)
                val m3uUrl = prefs.getString("m3u_url", "https://itv.19860519.xyz/output/tv.m3u") ?: "https://itv.19860519.xyz/output/tv.m3u"
                val channels = withContext(Dispatchers.IO) {
                    M3UParser.fetchAndParse(m3uUrl)
                }
                allChannels.clear()
                allChannels.addAll(channels)
                updateGroupList()
                progressBar.visibility = View.GONE
            } catch (e: Exception) {
                progressBar.visibility = View.GONE
                errorText.visibility = View.VISIBLE
                errorText.text = "加载失败: ${e.message}\n请检查网络或设置中的源地址"
            }
        }
    }
    
    private fun updateGroupList() {
        val groupSet = mutableSetOf<String>()
        for (ch in allChannels) {
            if (ch.group.isNotBlank()) groupSet.add(ch.group)
        }
        groups = listOf("全部") + groupSet.sorted()
        groupSpinner.adapter = ArrayAdapter(this, android.R.layout.simple_spinner_item, groups)
        groupSpinner.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onItemSelected(parent: AdapterView<*>?, view: View?, position: Int, id: Long) {
                filterChannelsByGroup(groups[position])
            }
            override fun onNothingSelected(parent: AdapterView<*>?) {}
        }
        filterChannelsByGroup("全部")
    }
    
    private fun filterChannelsByGroup(group: String) {
        currentChannels = if (group == "全部") {
            allChannels.toList()
        } else {
            allChannels.filter { it.group == group }
        }
        adapter = ChannelAdapter(currentChannels) { channel ->
            val intent = Intent(this, PlayerActivity::class.java)
            intent.putExtra("channel_name", channel.name)
            intent.putExtra("channel_url", channel.url)
            startActivity(intent)
        }
        recyclerView.adapter = adapter
    }
}
