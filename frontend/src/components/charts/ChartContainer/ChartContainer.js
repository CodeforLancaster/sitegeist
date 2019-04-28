import React, { Component } from 'react'
import { ResponsiveBarStyled } from '../BarChart/BarChart'
import './ChartContainer.css'
import { TabContent, Nav, NavItem, NavLink, Container, Row, Col } from 'reactstrap'
import classnames from 'classnames'

class ChartContainer extends Component {

  state = {
    selectedOption: 'all',
    bottom10: [],
    top10: [],
    hot10: [],
  }

  constructor() {
    super()
    // this.setSelected = this.setSelected.bind(this)
    this.loadData(this.state.selectedOption)
  }

  setSelected(option) {
    this.setState({ selectedOption: option })
    this.loadData(option)
  }

  loadData(option) {
    console.log('Going to fetch', option)
    fetch('/api/all/' + option)
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
      <Container className="mt-2 mb-5">
        <Nav tabs>
          <NavItem>
            <NavLink
              className={classnames({ active: this.state.selectedOption === 'all' })}
              onClick={() => { this.setSelected('all'); }}
            >
              All
              </NavLink>
          </NavItem>
          <NavItem>
            <NavLink
              className={classnames({ active: this.state.selectedOption === 'word' })}
              onClick={() => { this.setSelected('word'); }}
            >
              Words
              </NavLink>
          </NavItem>
          <NavItem>
            <NavLink
              className={classnames({ active: this.state.selectedOption === 'hashtag' })}
              onClick={() => { this.setSelected('hashtag'); }}
            >
              Hashtags
              </NavLink>
          </NavItem>
          <NavItem>
            <NavLink
              className={classnames({ active: this.state.selectedOption === 'mention' })}
              onClick={() => { this.setSelected('mention'); }}
            >
              Mentions
              </NavLink>
          </NavItem>
        </Nav>
        <TabContent>
          <Row className="mt-2">
            <Col>
              <ResponsiveBarStyled name={'Negative'} data={this.state.bottom10} color={'red_yellow_blue'}></ResponsiveBarStyled>
            </Col>
            <Col>
              <ResponsiveBarStyled name={'Positive'} data={this.state.top10} color={'accent'}></ResponsiveBarStyled>
            </Col>
          </Row>
          <Row className="mt-2">
            <Col>
              <ResponsiveBarStyled name={'Hot'} data={this.state.hot10} color={'category10'}></ResponsiveBarStyled>
            </Col>
          </Row>
        </TabContent>
      </Container>
    )
  }
}
export default ChartContainer
