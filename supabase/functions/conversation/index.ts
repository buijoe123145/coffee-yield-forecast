import { serve } from "https://deno.land/std@0.131.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const supabaseUrl = Deno.env.get("SUPABASE_URL") ?? "";
const supabaseKey = Deno.env.get("SUPABASE_ANON_KEY") ?? "";
const supabase = createClient(supabaseUrl, supabaseKey);

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  try {
    const { user_id, action, data } = await req.json();

    // Validate user_id and action
    if (!user_id || !action) {
      return new Response(
        JSON.stringify({ error: "user_id and action are required" }),
        { headers: { ...corsHeaders, "Content-Type": "application/json" }, status: 400 }
      );
    }

    // Check if farm exists
    let farm = null;
    const { data: farmData, error: farmError } = await supabase
      .from("farms")
      .select("*")
      .eq("user_id", user_id)
      .single();

    if (farmError) {
      if (farmError.code === "PGRST116") { // No rows found
        farm = null;
      } else {
        throw new Error(`Farm query error: ${farmError.message}`);
      }
    } else {
      farm = farmData;
    }

    if (action === "start") {
      if (farm) {
        return new Response(
          JSON.stringify({ message: "Please upload a new photo of your coffee trees." }),
          { headers: { ...corsHeaders, "Content-Type": "application/json" } }
        );
      } else {
        return new Response(
          JSON.stringify({ message: "What is the size of your farm in hectares?" }),
          { headers: { ...corsHeaders, "Content-Type": "application/json" } }
        );
      }
    }

    if (action === "submit_size") {
      const { size_hectares } = data || {};
      if (typeof size_hectares !== "number" || size_hectares <= 0) {
        return new Response(
          JSON.stringify({ error: "size_hectares must be a positive number" }),
          { headers: { ...corsHeaders, "Content-Type": "application/json" }, status: 400 }
        );
      }
      return new Response(
        JSON.stringify({ message: "How many coffee trees do you have?" }),
        { headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    if (action === "submit_trees") {
      const { tree_count } = data || {};
      if (typeof tree_count !== "number" || tree_count <= 0) {
        return new Response(
          JSON.stringify({ error: "tree_count must be a positive number" }),
          { headers: { ...corsHeaders, "Content-Type": "application/json" }, status: 400 }
        );
      }
      return new Response(
        JSON.stringify({ message: "Where is your farm located?" }),
        { headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    if (action === "submit_location") {
      const { location, size_hectares, tree_count } = data || {};
      if (!location || typeof size_hectares !== "number" || typeof tree_count !== "number") {
        return new Response(
          JSON.stringify({ error: "location, size_hectares, and tree_count are required" }),
          { headers: { ...corsHeaders, "Content-Type": "application/json" }, status: 400 }
        );
      }

      // Insert into farms
      const { data: newFarm, error: insertError } = await supabase
        .from("farms")
        .insert({ user_id, size_hectares, location })
        .select()
        .single();
      if (insertError) {
        throw new Error(`Failed to insert farm: ${insertError.message}`);
      }

      // Insert into trees
      const { error: treeError } = await supabase
        .from("trees")
        .insert({ farm_id: newFarm.farm_id, tree_count });
      if (treeError) {
        throw new Error(`Failed to insert trees: ${treeError.message}`);
      }

      return new Response(
        JSON.stringify({ message: "Please upload a photo of your coffee trees." }),
        { headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    if (action === "submit_photo") {
      const { image_url } = data || {};
      if (!image_url) {
        return new Response(
          JSON.stringify({ error: "image_url is required" }),
          { headers: { ...corsHeaders, "Content-Type": "application/json" }, status: 400 }
        );
      }
      if (!farm) {
        return new Response(
          JSON.stringify({ error: "Farm not found for this user" }),
          { headers: { ...corsHeaders, "Content-Type": "application/json" }, status: 404 }
        );
      }

      const farmId = farm.farm_id;

      // Store photo
      const { data: photo, error: photoError } = await supabase
        .from("photos")
        .insert({ farm_id: farmId, image_url })
        .select()
        .single();
      if (photoError) {
        throw new Error(`Failed to insert photo: ${photoError.message}`);
      }

      // Mock LLM API call (placeholder)
      const yieldEstimate = 1200 + Math.random() * 100;

      // Mock Weather API call (placeholder)
      const weatherData = { temperature: 25, rainfall: 10 };

      // Calculate yield
      if (!farm.size_hectares) {
        throw new Error("Farm size_hectares is missing");
      }
      const yield_kg_per_hectare = yieldEstimate * (farm.size_hectares / 5);

      // Store forecast
      const { error: forecastError } = await supabase
        .from("yieldforecasts")
        .insert({
          farm_id: farmId,
          photo_id: photo.photo_id,
          yield_kg_per_hectare,
          weather_data: weatherData,
        });
      if (forecastError) {
        throw new Error(`Failed to insert forecast: ${forecastError.message}`);
      }

      return new Response(
        JSON.stringify({ message: `Estimated yield: ${yield_kg_per_hectare.toFixed(2)} kg/hectare` }),
        { headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    return new Response(
      JSON.stringify({ error: "Invalid action" }),
      { headers: { ...corsHeaders, "Content-Type": "application/json" }, status: 400 }
    );
  } catch (error) {
    return new Response(
      JSON.stringify({ error: error.message }),
      { headers: { ...corsHeaders, "Content-Type": "application/json" }, status: 500 }
    );
  }
});