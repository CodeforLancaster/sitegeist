import React, { Component } from 'react'
import './Header.css'

class Header extends Component {
  render() {
    return (
      <header>
        <h1><span role="img" aria-label="">👻</span> SiteGeist</h1>
        <h2>Real-time analysis of the subjects generating the most positive and most negative reactions in a particular area, over the last 24 hours. Powered by AI.</h2>
      </header>
    )
  }
}

export default Header
