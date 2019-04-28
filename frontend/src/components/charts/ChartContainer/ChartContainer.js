import React, { Component } from 'react'
import './Header.css'

class ChartContainer extends Component {
  render() {
    return (
      <div id="selector" class="btn-group btn-group-toggle mb-4" data-toggle="buttons">
        <label class="btn btn-secondary active">
          <input type="radio" name="options" id="all" autocomplete="off" checked /> All
          </label>
        <label class="btn btn-secondary">
          <input type="radio" name="options" id="word" autocomplete="off" /> Words
          </label>
        <label class="btn btn-secondary">
          <input type="radio" name="options" id="hashtag" autocomplete="off" /> Hashtags
          </label>
        <label class="btn btn-secondary">
          <input type="radio" name="options" id="mention" autocomplete="off" /> Mentions
          </label>
      </div>
    )
  }
}
export default ChartContainer
