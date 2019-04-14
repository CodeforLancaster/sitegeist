import React, { Component } from 'react'
import './MapContainer.css'
import { Map, TileLayer, Marker, Popup, Polygon, Rectangle } from "react-leaflet"
import 'leaflet/dist/leaflet.css'
import L from 'leaflet'

delete L.Icon.Default.prototype._getIconUrl;

L.Icon.Default.mergeOptions({
  iconRetinaUrl: require('leaflet/dist/images/marker-icon-2x.png'),
  iconUrl: require('leaflet/dist/images/marker-icon.png'),
  shadowUrl: require('leaflet/dist/images/marker-shadow.png')
});


class MapContainer extends Component {

  constructor() {
    super()
    this.state = {
      lat: 51.505,
      lng: -0.09,
      zoom: 13,
      loc: undefined
    }
  }

  componentDidMount() {
    fetch('http://localhost:5001/api/loc')
      .then(res => res.json())
      .then(loc => {
        console.log('Location loaded:', loc)
        this.setState({...this.state, loc})
      })
  }

  render() {
    const position = [this.state.lat, this.state.lng]
    const loc = this.state.loc
    if (loc !== undefined)  {
      return (
        <Map className="map" center={position} zoom="12">
          <TileLayer
            attribution="&amp;copy <a href=&quot;http://osm.org/copyright&quot;>OpenStreetMap</a> contributors"
            url="https://cartodb-basemaps-{s}.global.ssl.fastly.net/light_all/{z}/{x}/{y}.png"
          />
          <Rectangle bounds={loc} />
        </Map>
      )
    }
    else {
      return (<p>Map Loading...</p>)
    }
  }
}

export default MapContainer
