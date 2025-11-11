query {
  BhuProject(offset: 0, limit: 1000, order: "name asc", domain: [])
  {
    id
    name
    code
    budget
    create_date
  }
}

query {
  BhuSurvey(
    offset: 0
    limit: 1000
  ) {
    id
    name
    survey_uuid
    khasra_number
    survey_date
    total_area
    acquired_area
    state
    notification4_generated
    district_name
    crop_type
    irrigation_type
    tree_development_stage
    tree_count
    trees_description
    has_house
    house_type
    house_area
    shed_area
    has_well
    well_type
    has_tubewell
    has_pond
    latitude
    longitude
    location_accuracy
    location_timestamp
    remarks
    landowner_pan_numbers
    landowner_aadhar_numbers
    user_id {
      id
      name
      login
    }
    project_id {
      id
      name
      code
      project_uuid
      description
      budget
      start_date
      end_date
      state
    }
    department_id {
      id
      name
      code
    }
    village_id {
      id
      name
      village_code
      village_uuid
      pincode
      population
      area_hectares
      district_id {
        id
        name
        code
      }
      tehsil_id {
        id
        name
      }
      state_id {
        id
        name
        code
      }
    }
    tehsil_id {
      id
      name
    }
    company_id {
      id
      name
    }
    landowner_ids {
      id
      name
      father_name
      gender
      age
      aadhar_number
      pan_number
      phone
      bank_name
      bank_branch
      account_number
      ifsc_code
      village_id {
        id
        name
      }
    }
  }
}
