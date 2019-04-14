import React, { Component } from 'react'
import './App.css'
import Header from './components/Header/Header'
import MapContainer from './components/MapContainer/MapContainer'

class App extends Component {
  render() {
    return (
      <div className="App">
        <Header/>
        <MapContainer/>
      </div>
    )
  }
}

export default App
