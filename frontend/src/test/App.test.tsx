import { render, screen } from '@testing-library/react'
import App from '../App'

test('renders appointment scheduling system', () => {
  render(<App />)
  const linkElement = screen.getByText(/Appointment Scheduling System/i)
  expect(linkElement).toBeInTheDocument()
})