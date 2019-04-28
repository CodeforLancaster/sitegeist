import React, { Component } from 'react'
import { ResponsiveBarStyled } from '../BarChart/BarChart'
import './ChartContainer.css'
import { parse } from 'ipaddr.js';

class ChartContainer extends Component {

  state = {
    selectedOption: 'all',
    bottom10: [],
    top10: [],
    hot10: [],
  }

  constructor() {
    super()
    this.handleChange = this.handleChange.bind(this)
  }

  handleChange(event) {
    const selected = event.target.id
    this.setState({ selectedOption: selected })
    fetch('http://localhost:5001/api/all/' + selected)
      .then(res => res.json())
      .then(data => {
        console.log('Data loaded:', data)
        const { bottom10, top10, hot10 } = data
        const parsed = this.parseData({ bottom10, top10, hot10 })
        this.setState({ ...this.state, ...parsed })
      })
      .catch(e => {
        console.error(e)
      })
  }

  parseData(data) {
    const parsed = {}
    for (const key in data) {
      parsed[key] = this.parseList(data[key])
    }
    return parsed
  }

  parseList(data) {
    return data.map(topic => {
      return {
        topic: topic[0],
        tweets: [1],
        sentiment: topic[2],
      }
    }).reverse()
  }

  render() {
    return (
      <div>
        <div id="selector" data-toggle="buttons" onChange={this.handleChange}>
          <label>
            <input type="radio" name="options" id="all" autoComplete="off" defaultChecked /> All
          </label>
          <label>
            <input type="radio" name="options" id="word" autoComplete="off" /> Words
          </label>
          <label>
            <input type="radio" name="options" id="hashtag" autoComplete="off" /> Hashtags
          </label>
          <label>
            <input type="radio" name="options" id="mention" autoComplete="off" /> Mentions
          </label>
        </div>
        <div className="chart-container">
          <ResponsiveBarStyled name={'Negative'} data={this.state.bottom10}></ResponsiveBarStyled>
          <ResponsiveBarStyled name={'Hot'} data={this.state.hot10}></ResponsiveBarStyled>
          <ResponsiveBarStyled name={'Positive'} data={this.state.top10}></ResponsiveBarStyled>
        </div>
      </div>
    )
  }
}
export default ChartContainer
