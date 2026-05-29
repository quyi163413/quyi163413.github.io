package com.iptv.player

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.recyclerview.widget.RecyclerView
import com.iptv.player.model.Channel

class ChannelAdapter(
    private val channels: List<Channel>,
    private val onItemClick: (Channel, Int) -> Unit
) : RecyclerView.Adapter<ChannelAdapter.ViewHolder>() {

    private var selectedPosition = -1

    fun setSelectedPosition(position: Int) {
        selectedPosition = position
        notifyDataSetChanged()
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val view = LayoutInflater.from(parent.context)
            .inflate(R.layout.item_channel, parent, false)
        return ViewHolder(view)
    }

    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        val channel = channels[position]
        holder.nameText.text = channel.name
        holder.itemView.isSelected = position == selectedPosition

        if (position == selectedPosition) {
            holder.nameText.setBackgroundResource(android.R.drawable.list_selector_background)
        } else {
            holder.nameText.background = null
        }

        holder.itemView.setOnClickListener {
            onItemClick(channel, position)
        }
    }

    override fun getItemCount() = channels.size

    class ViewHolder(itemView: View) : RecyclerView.ViewHolder(itemView) {
        val nameText: TextView = itemView.findViewById(R.id.channel_name)
    }
}
