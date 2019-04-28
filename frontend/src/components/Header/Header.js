import React, { Component } from 'react'
import './Header.css'
import lancasterRose from '../../assets/lancaster-rose.png'

class Header extends Component {
  render() {
    return (
      <header>
        <img alt="Lancaster Rose" src={lancasterRose}/>
        <h1>Sentimental Lancaster</h1>
        <p class="lead">Real time analysis of social media mood and sentiment in Lancaster, UK.</p>
      </header>
    )
  }
}

export default Header
